from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.attempts.models import Attempt, AttemptStatus

OPEN_STATUSES = (AttemptStatus.QUEUED, AttemptStatus.RUNNING)


class AttemptRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def add(self, attempt: Attempt) -> Attempt:
        self._db.add(attempt)
        await self._db.flush()
        return attempt

    async def get(self, attempt_id: str) -> Attempt | None:
        return await self._db.get(Attempt, attempt_id)

    async def get_by_key(self, session_id: str, key: str) -> Attempt | None:
        query = select(Attempt).where(
            Attempt.session_id == session_id, Attempt.idempotency_key == key
        )
        return (await self._db.scalars(query)).first()

    async def last_created_at(self, session_id: str) -> datetime | None:
        query = select(func.max(Attempt.created_at)).where(Attempt.session_id == session_id)
        latest: datetime | None = await self._db.scalar(query)
        return latest

    async def count_open(self) -> int:
        query = select(func.count()).select_from(Attempt).where(Attempt.status.in_(OPEN_STATUSES))
        return int(await self._db.scalar(query) or 0)

    async def list_open(self) -> Sequence[Attempt]:
        query = select(Attempt).where(
            Attempt.status.in_(OPEN_STATUSES), Attempt.run_id.is_not(None)
        )
        return (await self._db.scalars(query.order_by(Attempt.created_at))).all()

    async def list_recent(self, limit: int) -> Sequence[Attempt]:
        query = select(Attempt).order_by(Attempt.created_at.desc()).limit(limit)
        return (await self._db.scalars(query)).all()
