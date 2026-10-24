from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.memory_bank.models import MemoryKind, MemoryRecord


class MemoryRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def add(self, record: MemoryRecord) -> MemoryRecord:
        self._db.add(record)
        await self._db.flush()
        return record

    async def list_active(
        self,
        agent_id: str,
        subject_id: str,
        now: datetime,
        kind: MemoryKind | None = None,
        limit: int | None = None,
    ) -> list[MemoryRecord]:
        statement = select(MemoryRecord).where(
            MemoryRecord.agent_id == agent_id,
            MemoryRecord.subject_id == subject_id,
            MemoryRecord.expires_at > now,
        )
        if kind is not None:
            statement = statement.where(MemoryRecord.kind == kind)
        statement = statement.order_by(MemoryRecord.created_at.desc(), MemoryRecord.id)
        if limit is not None:
            statement = statement.limit(limit)
        return list((await self._db.scalars(statement)).all())

    async def delete_subject(self, agent_id: str, subject_id: str) -> int:
        statement = delete(MemoryRecord).where(
            MemoryRecord.agent_id == agent_id, MemoryRecord.subject_id == subject_id
        )
        result = await self._db.execute(statement)
        return int(getattr(result, "rowcount", 0) or 0)

    async def delete_subject_everywhere(self, subject_id: str) -> int:
        result = await self._db.execute(
            delete(MemoryRecord).where(MemoryRecord.subject_id == subject_id)
        )
        return int(getattr(result, "rowcount", 0) or 0)

    async def delete_expired(self, now: datetime) -> int:
        result = await self._db.execute(delete(MemoryRecord).where(MemoryRecord.expires_at <= now))
        return int(getattr(result, "rowcount", 0) or 0)
