from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.attempts.models import Attempt, AttemptOutcome
from agent_zero.config import Settings
from agent_zero.evals.wilson_interval import wilson_interval
from agent_zero.prober.campaign_models import Campaign, CampaignCaseRecord, CampaignPlan


def evidence_mode(settings: Settings) -> str:
    mode = settings.llm_mode.value
    if mode in {"live", "record"}:
        return "live"
    return "replayed" if mode == "replay" else "simulated"


def version_row(
    version: int, attempts: list[Attempt], cases: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    inconclusive = sum(a.outcome is AttemptOutcome.INCONCLUSIVE for a in attempts)
    pending = sum(a.outcome is None for a in attempts)
    violations = [a for a in attempts if a.outcome is AttemptOutcome.CONFIRMED_VIOLATION]
    evaluable = len(attempts) - inconclusive - pending
    interval = wilson_interval(len(violations), evaluable)
    first = violations[0] if violations else None
    case = cases.get(first.id, {}) if first is not None else {}
    return {
        "version": version,
        "queries": len(attempts),
        "evaluable": evaluable,
        "inconclusive": inconclusive,
        "pending": pending,
        "violations": len(violations),
        "success_rate": len(violations) / evaluable if evaluable else None,
        "ci_low": interval[0] if interval else None,
        "ci_high": interval[1] if interval else None,
        "queries_to_break": attempts.index(first) + 1 if first is not None else None,
        "censored": first is None,
        "first_break": (
            {"mutator": case.get("mutator") or "seed", "family": case.get("family")}
            if first is not None
            else None
        ),
    }


async def coevolution(db: AsyncSession, settings: Settings) -> dict[str, Any]:
    result: dict[str, Any] = {
        "budget": settings.prober_round_query_budget,
        "evidence_mode": evidence_mode(settings),
        "status": None,
        "versions": [],
        "summary": None,
    }
    campaign = await db.scalar(
        select(Campaign)
        .join(CampaignPlan, CampaignPlan.campaign_id == Campaign.id)
        .where(CampaignPlan.generation == "adaptive")
        .order_by(Campaign.created_at.desc())
        .limit(1)
    )
    if campaign is None:
        return result
    attempts = list(
        await db.scalars(
            select(Attempt)
            .where(Attempt.campaign_id == campaign.id, Attempt.origin == "autonomous")
            .order_by(Attempt.created_at, Attempt.id)
        )
    )
    cases = {
        str(row.attempt_id): row.case_json
        for row in await db.scalars(
            select(CampaignCaseRecord).where(CampaignCaseRecord.campaign_id == campaign.id)
        )
        if row.attempt_id
    }
    grouped: defaultdict[int, list[Attempt]] = defaultdict(list)
    for attempt in attempts:
        grouped[attempt.policy_version].append(attempt)
    rows = [version_row(version, items, cases) for version, items in sorted(grouped.items())]
    summary = {"baseline": rows[0], "latest": rows[-1]} if rows else None
    result.update(status=campaign.status, versions=rows, summary=summary)
    return result
