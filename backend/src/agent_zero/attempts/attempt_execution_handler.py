from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.arena.transactions import serialize_write
from agent_zero.attempts.activation_gate import activation_pending, active_version
from agent_zero.attempts.attempt_query_service import call_context
from agent_zero.attempts.conversation import previous_turns
from agent_zero.attempts.models import Attempt, AttemptOutcome, AttemptStatus
from agent_zero.attempts.repository import AttemptRepository
from agent_zero.events.event_store import EventStore
from agent_zero.events.models import EventType
from agent_zero.events.schemas import EventDraft
from agent_zero.fleet.fleet_builder import Fleet
from agent_zero.oracles.assessment_service import AssessmentService
from agent_zero.runtime.handlers import StepContext
from agent_zero.runtime.step_results import Advance, Complete, Fail, StepResult, Wait
from agent_zero.victim.arena_manifest import ARENA_HANDLER
from agent_zero.victim.tool_loop import ConversationExecutor


class AttemptExecutionHandler:
    name = ARENA_HANDLER

    def __init__(
        self,
        fleet: Fleet,
        executor: ConversationExecutor,
        events: EventStore,
        assessments: AssessmentService,
    ) -> None:
        self._fleet = fleet
        self._executor = executor
        self._events = events
        self._assessments = assessments

    async def _begin(self, db: AsyncSession, context: StepContext) -> Attempt | StepResult:
        attempt = await AttemptRepository(db).get(str(context.input["attempt_id"]))
        if attempt is None:
            return Fail(reason="Intento no disponible o sin herramientas.")
        if attempt.outcome is not None:
            return Complete(output={"attempt_id": attempt.id, "outcome": attempt.outcome.value})
        if attempt.status is not AttemptStatus.QUEUED:
            return attempt
        now = self._fleet.clock()
        settings = self._fleet.settings
        if await activation_pending(db, now, settings.defense_activation_hold_seconds):
            return Wait(until=now + timedelta(seconds=settings.runtime_poll_seconds))
        attempt.policy_version = await active_version(db)
        attempt.status = AttemptStatus.RUNNING
        attempt.updated_at = now
        return attempt

    async def step(self, context: StepContext) -> StepResult:
        if context.tools is None:
            return Fail(reason="Intento no disponible o sin herramientas.")
        async with self._fleet.database.sessions() as db:
            await serialize_write(db)
            attempt = await self._begin(db, context)
            if not isinstance(attempt, Attempt):
                return attempt
            if not context.checkpoint:
                await self._events.stage(
                    db,
                    EventDraft(
                        type=EventType.ATTEMPT_STARTED,
                        attempt_id=attempt.id,
                        session_id=attempt.session_id,
                        policy_version=attempt.policy_version,
                    ),
                    dedup_key=f"{attempt.id}:started",
                )
            history = [] if context.checkpoint else await previous_turns(db, attempt.id)
            await db.commit()
        scope = call_context(attempt)
        if not context.checkpoint:
            state = await self._executor.start(
                scope, context.principal, attempt.messages, history=history
            )
            return Advance(checkpoint=state)
        if context.checkpoint["phase"] != "complete":
            state = await self._executor.advance(
                scope, context.tools, context.checkpoint, attempt.messages
            )
            return Advance(checkpoint=state)
        reply = "\n".join(str(text) for text in context.checkpoint["replies"])
        await self._events.emit(
            EventDraft(
                type=EventType.ATTEMPT_COMPLETED,
                attempt_id=attempt.id,
                session_id=attempt.session_id,
                policy_version=attempt.policy_version,
                data={"reply": reply},
            ),
            dedup_key=f"{attempt.id}:completed",
        )
        assessment = await self._assessments.assess(
            scope, await self._events.for_attempt(attempt.id), reply
        )
        async with self._fleet.database.sessions() as db:
            await serialize_write(db)
            stored = await AttemptRepository(db).get(attempt.id)
            if stored is None:
                return Fail(reason="El intento dejó de existir.")
            stored.reply = reply
            stored.outcome = assessment.outcome
            stored.assessment = assessment.model_dump(mode="json")
            stored.status = (
                AttemptStatus.INCONCLUSIVE
                if assessment.outcome is AttemptOutcome.INCONCLUSIVE
                else AttemptStatus.EVALUATED
            )
            stored.updated_at = self._fleet.clock()
            await self._events.stage(
                db,
                EventDraft(
                    type=EventType.ATTEMPT_EVALUATED,
                    attempt_id=attempt.id,
                    session_id=attempt.session_id,
                    policy_version=attempt.policy_version,
                    data=assessment.model_dump(mode="json"),
                ),
                dedup_key=f"{attempt.id}:evaluated",
            )
            outcome = (
                "apparent_success"
                if assessment.outcome
                in {
                    AttemptOutcome.CONFIRMED_VIOLATION,
                    AttemptOutcome.CONTAINED_HONEYPOT,
                }
                else assessment.outcome.value
            )
            await self._events.stage_public(
                db,
                EventType.ATTEMPT_EVALUATED,
                attempt.policy_version,
                outcome=outcome,
                dedup_key=f"{attempt.id}:evaluated:public",
            )
            await db.commit()
        await self._events.dispatch_pending()
        return Complete(output={"attempt_id": attempt.id, "outcome": assessment.outcome.value})
