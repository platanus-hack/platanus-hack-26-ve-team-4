from collections.abc import Callable
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.runtime.models import Run, RunEventKind, RunStatus
from agent_zero.runtime.repository import RunRepository
from agent_zero.shared.clock import utc_now


class RunNotFoundError(LookupError):
    def __init__(self, run_id: str) -> None:
        super().__init__(f"No existe la ejecución {run_id}.")
        self.run_id = run_id


class RunCancelService:
    def __init__(self, db: AsyncSession, clock: Callable[[], datetime] = utc_now) -> None:
        self._db = db
        self._repository = RunRepository(db)
        self._clock = clock

    async def cancel(self, run_id: str) -> Run:
        run = await self._repository.get(run_id)
        if run is None:
            raise RunNotFoundError(run_id)
        if run.status.terminal:
            return run
        now = self._clock()
        run.status = RunStatus.CANCELLED
        run.resume_at = None
        run.updated_at = now
        await self._repository.add_event(
            run.run_id, run.step_index, RunEventKind.CANCELLED, "cancelada por el operador", now
        )
        await self._db.commit()
        return run
