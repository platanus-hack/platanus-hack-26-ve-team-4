from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.memory_bank.repository import MemoryRepository


class MemoryErasureService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._repository = MemoryRepository(db)

    async def erase_subject(self, subject_id: str) -> int:
        deleted = await self._repository.delete_subject_everywhere(subject_id)
        await self._db.commit()
        return deleted
