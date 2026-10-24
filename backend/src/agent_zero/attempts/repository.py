from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.attempts.models import Attempt, AttemptOutcome, AttemptStatus

IN_FLIGHT = (AttemptStatus.QUEUED, AttemptStatus.RUNNING)


class AttemptRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, attempt_id: str) -> Attempt | None:
        return await self.db.get(Attempt, attempt_id)

    async def by_key(self, session_id: str, key: str) -> Attempt | None:
        return await self.db.scalar(
            select(Attempt).where(Attempt.session_id == session_id, Attempt.idempotency_key == key)
        )

    async def in_flight(self, session_id: str | None = None, *, origin: str | None = None) -> int:
        query = select(func.count()).select_from(Attempt).where(Attempt.status.in_(IN_FLIGHT))
        if session_id is not None:
            query = query.where(Attempt.session_id == session_id)
        if origin is not None:
            query = query.where(Attempt.origin == origin)
        return int(await self.db.scalar(query) or 0)

    async def recent_count(self, session_id: str, since: datetime) -> int:
        return int(
            await self.db.scalar(
                select(func.count())
                .select_from(Attempt)
                .where(Attempt.session_id == session_id, Attempt.created_at >= since)
            )
            or 0
        )

    async def pending_runs(self) -> list[Attempt]:
        return list(await self.db.scalars(select(Attempt).where(Attempt.status.in_(IN_FLIGHT))))

    async def unprocessed_violations(self) -> list[Attempt]:
        return list(
            await self.db.scalars(
                select(Attempt).where(
                    Attempt.outcome == AttemptOutcome.CONFIRMED_VIOLATION,
                    ~Attempt.defense_processed,
                )
            )
        )

    async def needs_diversion(self, session_id: str) -> bool:
        violation = await self.db.scalar(
            select(Attempt.id)
            .where(
                Attempt.session_id == session_id,
                Attempt.outcome == AttemptOutcome.CONFIRMED_VIOLATION,
            )
            .limit(1)
        )
        return violation is not None
