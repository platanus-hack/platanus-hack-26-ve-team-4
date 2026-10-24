from collections.abc import Callable
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.runtime.handler_registry import HandlerRegistry
from agent_zero.runtime.models import Run, RunEventKind, RunStatus
from agent_zero.runtime.repository import RunRepository
from agent_zero.runtime.schemas import RunCreate
from agent_zero.shared.clock import utc_now
from agent_zero.shared.ids import new_id


class RunEnqueueService:
    def __init__(
        self,
        db: AsyncSession,
        registry: HandlerRegistry,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._db = db
        self._repository = RunRepository(db)
        self._registry = registry
        self._clock = clock

    async def enqueue(self, payload: RunCreate, *, commit: bool = True) -> Run:
        self._registry.get(payload.handler)
        if payload.idempotency_key is not None:
            existing = await self._repository.get_by_key(payload.idempotency_key)
            if existing is not None:
                return existing
        now = self._clock()
        run = Run(
            run_id=new_id("run"),
            agent_id=payload.agent_id,
            agent_version=payload.agent_version,
            handler=payload.handler,
            input_json=dict(payload.input),
            status=RunStatus.QUEUED,
            idempotency_key=payload.idempotency_key,
            attempts=0,
            checkpoint_json={},
            step_index=0,
            created_at=now,
            updated_at=now,
        )
        try:
            await self._repository.add(run)
            await self._repository.add_event(run.run_id, 0, RunEventKind.QUEUED, "", now)
            if commit:
                await self._db.commit()
            else:
                await self._db.flush()
        except IntegrityError:
            await self._db.rollback()
            key = payload.idempotency_key
            existing = await self._repository.get_by_key(key) if key else None
            if existing is None:
                raise
            return existing
        return run
