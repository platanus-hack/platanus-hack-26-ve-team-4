from collections.abc import Callable
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.identity.schemas import AgentPrincipal
from agent_zero.memory_bank.memory_access import READ_SCOPE
from agent_zero.memory_bank.memory_cipher import MemoryCipher
from agent_zero.memory_bank.memory_mapping import to_item
from agent_zero.memory_bank.models import MemoryKind
from agent_zero.memory_bank.principal_guard import PrincipalGuard
from agent_zero.memory_bank.repository import MemoryRepository
from agent_zero.memory_bank.schemas import MemoryItem
from agent_zero.shared.clock import utc_now


class MemoryReadService:
    def __init__(
        self,
        db: AsyncSession,
        cipher: MemoryCipher,
        guard: PrincipalGuard,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._cipher = cipher
        self._guard = guard
        self._clock = clock
        self._repository = MemoryRepository(db)

    async def recall(
        self,
        principal: AgentPrincipal,
        subject_id: str,
        kind: MemoryKind | None = None,
        limit: int | None = None,
    ) -> list[MemoryItem]:
        verified = await self._guard.authorize(principal, READ_SCOPE)
        records = await self._repository.list_active(
            verified.agent_id, subject_id, self._clock(), kind, limit
        )
        return [to_item(record, self._cipher) for record in records]
