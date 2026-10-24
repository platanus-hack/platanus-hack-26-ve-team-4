from collections.abc import Callable
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.armor.model_armor import ModelArmor
from agent_zero.armor.models import Surface
from agent_zero.config import Settings
from agent_zero.identity.schemas import AgentPrincipal
from agent_zero.memory_bank.errors import MemoryRejectedError
from agent_zero.memory_bank.memory_access import WRITE_SCOPE, require_scope
from agent_zero.memory_bank.memory_cipher import MemoryCipher
from agent_zero.memory_bank.memory_mapping import to_item
from agent_zero.memory_bank.models import MemoryRecord
from agent_zero.memory_bank.repository import MemoryRepository
from agent_zero.memory_bank.schemas import MemoryItem, MemoryWriteRequest
from agent_zero.shared.clock import utc_now
from agent_zero.shared.ids import new_id


class MemoryWriteService:
    def __init__(
        self,
        db: AsyncSession,
        settings: Settings,
        cipher: MemoryCipher,
        armor: ModelArmor | None = None,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._db = db
        self._default_ttl_days = settings.memory_default_ttl_days
        self._cipher = cipher
        self._armor = armor or ModelArmor()
        self._clock = clock
        self._repository = MemoryRepository(db)

    async def write(self, principal: AgentPrincipal, request: MemoryWriteRequest) -> MemoryItem:
        require_scope(principal, WRITE_SCOPE)
        verdict = self._armor.screen(request.content, Surface.MEMORY_WRITE)
        if verdict.blocked or verdict.sanitized_text is None:
            detail = "; ".join(finding.detail for finding in verdict.findings)
            raise MemoryRejectedError(detail or "contenido no permitido")
        now = self._clock()
        ttl_days = request.ttl_days or self._default_ttl_days
        record = MemoryRecord(
            id=new_id("mem"),
            agent_id=principal.agent_id,
            subject_id=request.subject_id,
            kind=request.kind,
            ciphertext=self._cipher.encrypt(verdict.sanitized_text),
            created_at=now,
            expires_at=now + timedelta(days=ttl_days),
            source_run_id=request.source_run_id,
            source_trace_id=request.source_trace_id,
        )
        await self._repository.add(record)
        await self._db.commit()
        return to_item(record, self._cipher)
