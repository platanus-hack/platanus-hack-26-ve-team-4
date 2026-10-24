import asyncio
import contextlib
import logging

from agent_zero.analyzer.finding_service import FindingService
from agent_zero.arena.round_state import round_resetting
from agent_zero.arena.transactions import serialize_write
from agent_zero.attempts.models import AttemptOutcome, AttemptStatus
from agent_zero.attempts.repository import AttemptRepository
from agent_zero.events.event_store import EventStore
from agent_zero.events.models import EventType
from agent_zero.events.schemas import EventDraft
from agent_zero.fleet.fleet_builder import Fleet
from agent_zero.oracles.schemas import Assessment
from agent_zero.patches.defense_scheduler import DefenseScheduler
from agent_zero.runtime.models import RunStatus
from agent_zero.runtime.run_query_service import query_run

logger = logging.getLogger(__name__)


class AttemptWorker:
    def __init__(
        self, fleet: Fleet, events: EventStore, findings: FindingService, defense: DefenseScheduler
    ) -> None:
        self._fleet = fleet
        self._events = events
        self._findings = findings
        self._defense = defense
        self._stopping = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    async def tick(self) -> None:
        await self._events.dispatch_pending()
        async with self._fleet.database.sessions() as db:
            if await round_resetting(db):
                return
        await self._failures()
        async with self._fleet.database.sessions() as db:
            pending = await AttemptRepository(db).unprocessed_violations()
        for attempt in pending:
            await self._findings.record(attempt, Assessment.model_validate(attempt.assessment))
            async with self._fleet.database.sessions() as db:
                row = await AttemptRepository(db).get(attempt.id)
                if row is not None:
                    row.defense_processed = True
                    await db.commit()
        await self._defense.tick()

    async def _failures(self) -> None:
        async with self._fleet.database.sessions() as db:
            await serialize_write(db)
            attempts = await AttemptRepository(db).pending_runs()
            for attempt in attempts:
                run = await query_run(db, attempt.run_id)
                if run is not None and run.status in {RunStatus.FAILED, RunStatus.CANCELLED}:
                    assessment = Assessment(
                        outcome=AttemptOutcome.INCONCLUSIVE,
                        verdicts=[],
                        detail=run.failure_reason or "Run cancelado.",
                    )
                    attempt.status = AttemptStatus.INCONCLUSIVE
                    attempt.outcome = AttemptOutcome.INCONCLUSIVE
                    attempt.assessment = assessment.model_dump(mode="json")
                    attempt.updated_at = self._fleet.clock()
                    await self._events.stage(
                        db,
                        EventDraft(
                            type=EventType.ATTEMPT_EVALUATED,
                            attempt_id=attempt.id,
                            session_id=attempt.session_id,
                            policy_version=attempt.policy_version,
                            data=attempt.assessment,
                        ),
                        dedup_key=f"{attempt.id}:evaluated",
                    )
                    await self._events.stage_public(
                        db,
                        EventType.ATTEMPT_EVALUATED,
                        attempt.policy_version,
                        outcome="inconclusive",
                        dedup_key=f"{attempt.id}:evaluated:public",
                    )
            await db.commit()
        await self._events.dispatch_pending()

    def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._stopping.clear()
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._stopping.set()
        if self._task is not None:
            await self._task

    async def _loop(self) -> None:
        while not self._stopping.is_set():
            try:
                await self.tick()
            except Exception:
                logger.exception(
                    "Falló un paso del núcleo; se reintentará desde el estado persistido."
                )
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(
                    self._stopping.wait(), self._fleet.settings.runtime_poll_seconds
                )
