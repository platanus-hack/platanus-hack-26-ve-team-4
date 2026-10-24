import asyncio
import contextlib
import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.attempts.attempt_events import AttemptEvents
from agent_zero.attempts.execution import ArenaWiring, EvaluationInput
from agent_zero.attempts.models import Attempt, AttemptOutcome, AttemptStatus
from agent_zero.attempts.repository import AttemptRepository
from agent_zero.runtime.run_status_service import RunState, read_run_states
from agent_zero.shared.clock import utc_now

NO_EVALUATOR = "oráculos no disponibles: no hay veredicto para este intento"
logger = logging.getLogger(__name__)


class AttemptTracker:
    """Sigue el run de cada intento abierto y publica sus transiciones.

    queued → running cuando el run empieza; al terminar, `evaluated` con el veredicto del
    evaluador o `inconclusive` si el run falló, se canceló o no hay evaluador.
    """

    def __init__(
        self,
        sessions: Callable[[], AbstractAsyncContextManager[AsyncSession]],
        wiring: ArenaWiring,
        events: AttemptEvents,
        poll_seconds: float,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._sessions = sessions
        self._wiring = wiring
        self._events = events
        self._poll_seconds = poll_seconds
        self._clock = clock
        self._task: asyncio.Task[None] | None = None
        self._stopping = asyncio.Event()

    async def sync_once(self) -> int:
        changed = 0
        async with self._sessions() as db:
            attempts = await AttemptRepository(db).list_open()
            states = await read_run_states(db, [a.run_id for a in attempts if a.run_id])
            for attempt in attempts:
                state = states.get(attempt.run_id or "")
                if state is not None and await self._advance(attempt, state):
                    changed += 1
            await db.commit()
        return changed

    async def _advance(self, attempt: Attempt, state: RunState) -> bool:
        if state.terminal:
            if attempt.status is AttemptStatus.QUEUED:
                self._mark_running(attempt)
            await self._finish(attempt, state)
            return True
        if state.started and attempt.status is AttemptStatus.QUEUED:
            self._mark_running(attempt)
            return True
        return False

    def _mark_running(self, attempt: Attempt) -> None:
        attempt.status = AttemptStatus.RUNNING
        attempt.updated_at = self._clock()
        self._events.started(attempt)

    async def _finish(self, attempt: Attempt, state: RunState) -> None:
        attempt.output_json = state.output
        attempt.reply = _reply(state.output)
        if not state.succeeded:
            self._close(attempt, AttemptOutcome.INCONCLUSIVE, state.failure_reason or state.status)
        elif self._wiring.evaluator is None:
            self._close(attempt, AttemptOutcome.INCONCLUSIVE, NO_EVALUATOR)
        else:
            evaluation = EvaluationInput(
                attempt_id=attempt.id,
                session_id=attempt.session_id,
                objective_id=attempt.objective_id,
                policy_version=attempt.policy_version,
                route=attempt.route,
                run_id=state.run_id,
                output=state.output,
            )
            try:
                verdict = await self._wiring.evaluator.evaluate(evaluation)
            except Exception as error:
                logger.exception("El evaluador falló en el intento %s", attempt.id)
                self._close(
                    attempt, AttemptOutcome.INCONCLUSIVE, f"evaluador: {type(error).__name__}"
                )
            else:
                self._close(attempt, verdict, None)
        self._events.finished(attempt)

    def _close(self, attempt: Attempt, outcome: AttemptOutcome, reason: str | None) -> None:
        attempt.outcome = outcome
        attempt.status = (
            AttemptStatus.INCONCLUSIVE
            if outcome is AttemptOutcome.INCONCLUSIVE
            else AttemptStatus.EVALUATED
        )
        attempt.failure_reason = reason
        attempt.updated_at = self._clock()

    def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._stopping.clear()
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._stopping.set()
        if self._task is not None:
            await self._task
            self._task = None

    async def _loop(self) -> None:
        while not self._stopping.is_set():
            try:
                await self.sync_once()
            except Exception:
                logger.exception(
                    "Falló la sincronización de intentos; se reintenta en el próximo ciclo"
                )
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self._stopping.wait(), self._poll_seconds)


def _reply(output: dict[str, Any] | None) -> str | None:
    reply = (output or {}).get("reply")
    return reply if isinstance(reply, str) else None
