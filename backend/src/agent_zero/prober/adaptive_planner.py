from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.attempts.models import Attempt, AttemptOutcome
from agent_zero.config import Settings
from agent_zero.events.event_delivery import to_trace
from agent_zero.events.event_store import EventStore
from agent_zero.events.models import EventRecord, EventType, Visibility
from agent_zero.events.schemas import TraceEvent
from agent_zero.policies.repository import PolicyRepository
from agent_zero.prober.adaptive_candidates import (
    SEED_ARM,
    Candidate,
    all_arms,
    candidate,
)
from agent_zero.prober.campaign_models import Campaign, CampaignCaseRecord
from agent_zero.prober.feedback import signal_from
from agent_zero.prober.strategy_selector import Arm, Pull, StrategySelector

EVIDENCE_OUTCOMES = frozenset(
    {AttemptOutcome.PREVENTED, AttemptOutcome.NOT_ACHIEVED, AttemptOutcome.CONTAINED_HONEYPOT}
)


@dataclass(frozen=True)
class Hold:
    pass


@dataclass(frozen=True)
class Finish:
    reason: str


@dataclass
class RoundStats:
    queries: int = 0
    violations: int = 0
    mutator: str = ""
    last_update: datetime | None = None


@dataclass
class Snapshot:
    campaign: Campaign
    index: int
    active: int
    rows: list[CampaignCaseRecord]
    attempts: dict[str, Attempt]
    rounds: dict[int, RoundStats]


def mutator_of(row: CampaignCaseRecord) -> str:
    return str(row.case_json.get("mutator") or SEED_ARM)


class AdaptivePlanner:
    def __init__(
        self, settings: Settings, clock: Callable[[], datetime], events: EventStore | None = None
    ) -> None:
        self._settings = settings
        self._clock = clock
        self._events = events
        self._announced: set[str] = set()

    async def next(
        self, db: AsyncSession, campaign: Campaign, index: int
    ) -> CampaignCaseRecord | Hold | Finish:
        active = (await PolicyRepository(db).active()).version
        rows = list(
            await db.scalars(
                select(CampaignCaseRecord)
                .where(CampaignCaseRecord.campaign_id == campaign.id)
                .order_by(CampaignCaseRecord.index)
            )
        )
        attempts = {
            attempt.id: attempt
            for attempt in await db.scalars(
                select(Attempt).where(Attempt.id.in_(campaign.attempt_ids))
            )
        }
        rounds = self._rounds(rows, attempts)
        staged = await self._close_rounds(db, campaign, rounds, active)
        decision = await self._decide(db, Snapshot(campaign, index, active, rows, attempts, rounds))
        await db.commit()
        if staged and self._events is not None:
            self._announced.update(staged)
            await self._events.dispatch_pending()
        return decision

    def _rounds(
        self, rows: list[CampaignCaseRecord], attempts: dict[str, Attempt]
    ) -> dict[int, RoundStats]:
        rounds: dict[int, RoundStats] = defaultdict(RoundStats)
        for row in rows:
            attempt = attempts.get(row.attempt_id or "")
            if attempt is None:
                continue
            stats = rounds[attempt.policy_version]
            stats.queries += 1
            stats.last_update = max(filter(None, [stats.last_update, attempt.updated_at]))
            if attempt.outcome is AttemptOutcome.CONFIRMED_VIOLATION:
                stats.violations += 1
                stats.mutator = stats.mutator or mutator_of(row)
        return rounds

    async def _close_rounds(
        self, db: AsyncSession, campaign: Campaign, rounds: dict[int, RoundStats], active: int
    ) -> list[str]:
        if self._events is None:
            return []
        budget = self._settings.prober_round_query_budget
        closed = [
            version
            for version, stats in sorted(rounds.items())
            if (version < active or stats.queries >= budget)
            and f"{campaign.id}:{version}" not in self._announced
        ]
        for version in closed:
            stats = rounds[version]
            await self._events.stage_public(
                db,
                EventType.PROBE_ROUND_CLOSED,
                version,
                dedup_key=f"probe-round:{campaign.id}:{version}",
                probe_round=version,
                queries=stats.queries,
                violations=stats.violations,
                mutator=stats.mutator,
            )
        return [f"{campaign.id}:{version}" for version in closed]

    async def _decide(
        self, db: AsyncSession, snapshot: Snapshot
    ) -> CampaignCaseRecord | Hold | Finish:
        campaign, index, active = snapshot.campaign, snapshot.index, snapshot.active
        rows, attempts = snapshot.rows, snapshot.attempts
        current = snapshot.rounds.get(active, RoundStats())
        if current.queries >= self._settings.prober_round_query_budget:
            return self._round_over(current)
        if await PolicyRepository(db).pending() is not None:
            return self._await_defense(max((a.updated_at for a in attempts.values()), default=None))
        history = await self._history(db, rows, attempts)
        seen = {row.digest for row in rows}
        options: dict[Arm, Candidate] = {}
        for arm in all_arms():
            found = candidate(arm, campaign.id, index, active, seen)
            if found is not None:
                options[arm] = found
        if not options:
            return Finish("unique_cases_exhausted")
        chosen = StrategySelector(campaign.id).choose(list(options), history, active)
        if chosen is None:
            return self._round_over(current)
        picked = options[chosen]
        row = CampaignCaseRecord(
            campaign_id=campaign.id,
            index=index,
            status="ready",
            customer_id=picked.customer,
            case_json=picked.case.model_dump(mode="json"),
            digest=picked.digest,
            session_id=None,
            attempt_id=None,
            error="",
        )
        db.add(row)
        return row

    def _round_over(self, current: RoundStats) -> Hold | Finish:
        if current.violations == 0:
            return Finish("held_within_budget")
        return self._await_defense(current.last_update)

    def _await_defense(self, since: datetime | None) -> Hold | Finish:
        waited = self._clock() - (since or self._clock())
        if waited > timedelta(seconds=self._settings.prober_round_close_wait_seconds):
            return Finish("defender_did_not_close")
        return Hold()

    async def _history(
        self, db: AsyncSession, rows: list[CampaignCaseRecord], attempts: dict[str, Attempt]
    ) -> list[Pull]:
        needed = [a.id for a in attempts.values() if a.outcome in EVIDENCE_OUTCOMES]
        events: dict[str, list[TraceEvent]] = defaultdict(list)
        if needed:
            for record in await db.scalars(
                select(EventRecord)
                .where(
                    EventRecord.attempt_id.in_(needed),
                    EventRecord.visibility == Visibility.OPERATOR,
                    EventRecord.type.in_([EventType.TOOL_DENIED, EventType.TOOL_PROPOSED]),
                )
                .order_by(EventRecord.id)
            ):
                events[str(record.attempt_id)].append(to_trace(record))
        pulls: list[Pull] = []
        for row in rows:
            attempt = attempts.get(row.attempt_id or "")
            if attempt is None or attempt.outcome is None:
                continue
            arm = (str(row.case_json["objective_id"]), mutator_of(row))
            pulls.append(
                Pull(arm, attempt.policy_version, signal_from(attempt, events[attempt.id]))
            )
        return pulls
