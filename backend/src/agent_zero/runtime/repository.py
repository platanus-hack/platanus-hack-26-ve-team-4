from datetime import datetime

from sqlalchemy import and_, case, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.runtime.models import Run, RunEvent, RunEventKind, RunStatus


class RunRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def add(self, run: Run) -> Run:
        self._db.add(run)
        await self._db.flush()
        return run

    async def get(self, run_id: str) -> Run | None:
        return await self._db.get(Run, run_id)

    async def get_by_key(self, key: str) -> Run | None:
        result = await self._db.execute(select(Run).where(Run.idempotency_key == key))
        return result.scalar_one_or_none()

    async def ready_ids(
        self,
        now: datetime,
        in_flight: frozenset[str],
        limit: int,
        priority: frozenset[str] = frozenset(),
    ) -> list[str]:
        due = or_(
            Run.status == RunStatus.QUEUED,
            and_(Run.status == RunStatus.WAITING, Run.resume_at <= now),
            Run.status == RunStatus.RUNNING,
        )
        rank = case((Run.handler.in_(priority), 0), else_=1) if priority else literal(1)
        query = (
            select(Run.run_id)
            .where(due)
            .order_by(rank, Run.created_at)
            .limit(limit + len(in_flight))
        )
        result = await self._db.execute(query)
        return [run_id for run_id in result.scalars() if run_id not in in_flight][:limit]

    async def add_event(
        self, run_id: str, step_index: int, kind: RunEventKind, detail: str, at: datetime
    ) -> None:
        self._db.add(
            RunEvent(run_id=run_id, step_index=step_index, kind=kind, detail=detail, at=at)
        )
        await self._db.flush()

    async def events(self, run_id: str) -> list[RunEvent]:
        result = await self._db.execute(
            select(RunEvent).where(RunEvent.run_id == run_id).order_by(RunEvent.id)
        )
        return list(result.scalars())
