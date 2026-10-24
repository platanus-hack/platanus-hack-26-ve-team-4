from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.attempts.attempt_events import AttemptEvents
from agent_zero.attempts.errors import TargetUnavailableError
from agent_zero.attempts.execution import ArenaTarget, ArenaWiring
from agent_zero.attempts.models import Attempt, AttemptOrigin, AttemptStatus
from agent_zero.attempts.rate_limits import check_queue_capacity, check_session_interval
from agent_zero.attempts.repository import AttemptRepository
from agent_zero.attempts.schemas import AttemptCreate
from agent_zero.config import Settings
from agent_zero.runtime.handler_registry import HandlerRegistry, UnknownHandlerError
from agent_zero.runtime.run_enqueue_service import RunEnqueueService
from agent_zero.runtime.schemas import RunCreate
from agent_zero.sessions.models import ArenaSession
from agent_zero.shared.clock import utc_now
from agent_zero.shared.ids import new_id


@dataclass(frozen=True)
class Submission:
    attempt: Attempt
    created: bool


class AttemptSubmissionService:
    def __init__(
        self,
        db: AsyncSession,
        settings: Settings,
        wiring: ArenaWiring,
        handlers: HandlerRegistry,
        events: AttemptEvents,
    ) -> None:
        self._db = db
        self._repository = AttemptRepository(db)
        self._settings = settings
        self._wiring = wiring
        self._handlers = handlers
        self._events = events

    async def submit(self, session: ArenaSession, payload: AttemptCreate) -> Submission:
        existing = await self._repository.get_by_key(session.id, payload.idempotency_key)
        if existing is not None:
            return Submission(await self._ensure_run(existing, session), created=False)
        target = self._available_target()
        now = utc_now()
        check_session_interval(
            await self._repository.last_created_at(session.id),
            now,
            self._settings.attempt_min_interval_seconds,
        )
        check_queue_capacity(
            await self._repository.count_open(), self._settings.attempt_queue_limit
        )
        attempt = Attempt(
            id=new_id("attempt"),
            session_id=session.id,
            origin=AttemptOrigin.AUDIENCE,
            idempotency_key=payload.idempotency_key,
            messages=payload.turns,
            objective_id=payload.objective_id,
            policy_version=self._wiring.policy_version(),
            route=session.route,
            status=AttemptStatus.QUEUED,
            created_at=now,
            updated_at=now,
        )
        try:
            await self._repository.add(attempt)
            await self._db.commit()
        except IntegrityError:
            await self._db.rollback()
            raced = await self._repository.get_by_key(session.id, payload.idempotency_key)
            if raced is None:
                raise
            return Submission(await self._ensure_run(raced, session), created=False)
        self._events.queued(attempt)
        return Submission(await self._enqueue(attempt, session, target), created=True)

    def _available_target(self) -> ArenaTarget:
        target = self._wiring.target
        if target is None:
            raise TargetUnavailableError("La víctima de la arena todavía no está disponible.")
        try:
            self._handlers.get(target.handler)
        except UnknownHandlerError as error:
            raise TargetUnavailableError(
                "La víctima de la arena todavía no está disponible."
            ) from error
        return target

    async def _ensure_run(self, attempt: Attempt, session: ArenaSession) -> Attempt:
        if attempt.run_id is not None or not attempt.status.open:
            return attempt
        return await self._enqueue(attempt, session, self._available_target())

    async def _enqueue(
        self, attempt: Attempt, session: ArenaSession, target: ArenaTarget
    ) -> Attempt:
        run = await RunEnqueueService(self._db, self._handlers).enqueue(
            RunCreate(
                agent_id=target.agent_id,
                agent_version=target.agent_version,
                handler=target.handler,
                input={
                    "attempt_id": attempt.id,
                    "session_id": session.id,
                    "customer_id": session.customer_id,
                    "messages": list(attempt.messages),
                    "objective_id": attempt.objective_id,
                    "policy_version": attempt.policy_version,
                    "route": attempt.route.value,
                },
                idempotency_key=f"attempt:{attempt.id}",
            )
        )
        attempt.run_id = run.run_id
        attempt.updated_at = utc_now()
        await self._db.commit()
        return attempt
