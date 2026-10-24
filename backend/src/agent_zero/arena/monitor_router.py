from typing import Any

from fastapi import APIRouter
from sqlalchemy import select

from agent_zero.arena.dependencies import Core
from agent_zero.arena.monitor_view import attempt_row, usage_by_attempt, usage_view
from agent_zero.prober.campaign_models import CampaignCaseRecord
from agent_zero.registry.dependencies import OperatorOnly

router = APIRouter(prefix="/api/operator", tags=["operator"], dependencies=[OperatorOnly])


async def campaign_families(core: Core) -> dict[str, str]:
    async with core.fleet.database.sessions() as db:
        rows = await db.scalars(
            select(CampaignCaseRecord).where(CampaignCaseRecord.attempt_id.is_not(None))
        )
        return {
            row.attempt_id: row.case_json["family"]
            for row in rows
            if row.attempt_id and isinstance(row.case_json.get("family"), str)
        }


@router.get("/monitor")
async def monitor(core: Core) -> dict[str, Any]:
    """Vista de la empresa: cada intento con su consumo de modelo, familia y parche."""
    attempts = await core.attempts.all()
    findings = await core.findings.all()
    policies = await core.policies.all()
    families = await campaign_families(core)
    by_attempt = usage_by_attempt(core.llm.ledger.records())
    finding_of = {
        attempt_id: finding for finding in findings for attempt_id in finding["attempt_ids"]
    }
    return {
        "llm_mode": core.llm.mode.value,
        "attempts": [
            attempt_row(
                attempt,
                by_attempt.get(attempt.id, []),
                finding_of.get(attempt.id),
                families.get(attempt.id),
                policies,
            )
            for attempt in attempts
        ],
        "totals": usage_view(
            record for attempt in attempts for record in by_attempt.get(attempt.id, [])
        ),
    }
