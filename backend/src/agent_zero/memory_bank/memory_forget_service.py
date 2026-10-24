from collections.abc import Callable
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.identity.schemas import AgentPrincipal
from agent_zero.memory_bank.memory_access import WRITE_SCOPE, require_scope
from agent_zero.memory_bank.repository import MemoryRepository
from agent_zero.shared.clock import utc_now


class MemoryForgetService:
    def __init__(self, db: AsyncSession, clock: Callable[[], datetime] = utc_now) -> None:
        self._db = db
        self._clock = clock
        self._repository = MemoryRepository(db)

    async def forget_subject(self, principal: AgentPrincipal, subject_id: str) -> int:
        require_scope(principal, WRITE_SCOPE)
        deleted = await self._repository.delete_subject(principal.agent_id, subject_id)
        await self._db.commit()
        return deleted

    async def purge_expired(self) -> int:
        deleted = await self._repository.delete_expired(self._clock())
        await self._db.commit()
        return deleted
