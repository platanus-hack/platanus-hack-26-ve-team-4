from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy import select

from agent_zero.analyzer.models import FindingExplanation, FindingRecord, FindingStatus
from agent_zero.arena.transactions import serialize_write
from agent_zero.attempts.models import Attempt
from agent_zero.events.event_store import EventStore
from agent_zero.events.models import EventType
from agent_zero.oracles.schemas import Assessment
from agent_zero.policies.validator_catalog import CONTROL_REASONS, OBJECTIVE_CONTROLS
from agent_zero.shared.clock import utc_now
from agent_zero.shared.database import Database
from agent_zero.shared.ids import new_id

OBJECTIVE_TOOLS = {
    "OBJ-ORDER": "get_order",
    "OBJ-REFUND": "request_refund",
    "OBJ-MEMORY": "save_memory",
}


def finding_view(row: FindingRecord) -> dict[str, Any]:
    return {
        "id": row.id,
        "objective_id": row.objective_id,
        "tool": row.tool,
        "missing_control": row.missing_control,
        "affected_policy_version": row.affected_policy_version,
        "attempt_ids": row.attempt_ids,
        "evidence_event_ids": row.evidence_event_ids,
        "probable_cause": row.probable_cause,
        "status": row.status.value,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }


class FindingService:
    def __init__(
        self,
        database: Database,
        events: EventStore,
        enrich: Callable[[str, str], Awaitable[None]] | None = None,
    ) -> None:
        self._database = database
        self._events = events
        self._enrich = enrich

    async def record(self, attempt: Attempt, assessment: Assessment) -> None:
        for verdict in assessment.verdicts:
            if not verdict.violated:
                continue
            tool = OBJECTIVE_TOOLS[verdict.objective_id]
            control = "+".join(OBJECTIVE_CONTROLS[verdict.objective_id])
            fingerprint = f"{verdict.objective_id}:{tool}:{control}"
            async with self._database.sessions() as db:
                await serialize_write(db)
                row = await db.scalar(
                    select(FindingRecord).where(FindingRecord.fingerprint == fingerprint)
                )
                created = row is None
                if row is None:
                    row = FindingRecord(
                        id=new_id("finding"),
                        fingerprint=fingerprint,
                        objective_id=verdict.objective_id,
                        tool=tool,
                        missing_control=control,
                        affected_policy_version=attempt.policy_version,
                        attempt_ids=[],
                        evidence_event_ids=[],
                        probable_cause=CONTROL_REASONS[verdict.objective_id],
                        status=FindingStatus.OPEN,
                        created_at=utc_now(),
                        updated_at=utc_now(),
                    )
                    db.add(row)
                if attempt.id not in row.attempt_ids:
                    row.attempt_ids = [*row.attempt_ids, attempt.id]
                    row.evidence_event_ids = sorted(
                        set(row.evidence_event_ids) | set(verdict.evidence_event_ids)
                    )
                    row.updated_at = utc_now()
                    if row.status is FindingStatus.MITIGATED:
                        row.status = FindingStatus.REOPENED
                if created:
                    await self._events.stage_public(
                        db,
                        EventType.FINDING_OPENED,
                        attempt.policy_version,
                        finding_id=row.id,
                        objective_id=row.objective_id,
                        dedup_key=f"finding:{row.id}:opened",
                    )
                await db.commit()
            await self._events.dispatch_pending()
            if self._enrich is not None:
                await self._enrich(row.id, attempt.id)

    async def all(self) -> list[dict[str, Any]]:
        async with self._database.sessions() as db:
            rows = await db.scalars(select(FindingRecord).order_by(FindingRecord.created_at))
            result = []
            for row in rows:
                explanation = await db.scalar(
                    select(FindingExplanation)
                    .where(FindingExplanation.finding_id == row.id)
                    .order_by(FindingExplanation.created_at.desc())
                    .limit(1)
                )
                item = finding_view(row)
                item["analysis"] = (
                    None
                    if explanation is None
                    else {
                        "status": explanation.status,
                        "advisory": True,
                        "attempt_id": explanation.attempt_id,
                        "error": explanation.error,
                        **explanation.explanation,
                    }
                )
                result.append(item)
            return result

    async def mitigate(self, finding_ids: list[str]) -> None:
        async with self._database.sessions() as db:
            for finding_id in finding_ids:
                row = await db.get(FindingRecord, finding_id)
                if row is not None:
                    row.status = FindingStatus.MITIGATED
                    row.updated_at = utc_now()
            await db.commit()

    async def reconcile_after_rollback(self, active_rules: list[str]) -> None:
        async with self._database.sessions() as db:
            for row in await db.scalars(
                select(FindingRecord).where(FindingRecord.status == FindingStatus.MITIGATED)
            ):
                if not set(row.missing_control.split("+")) <= set(active_rules):
                    row.status = FindingStatus.REOPENED
                    row.updated_at = utc_now()
            await db.commit()
