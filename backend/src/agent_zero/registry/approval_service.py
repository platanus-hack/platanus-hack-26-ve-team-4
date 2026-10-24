from collections.abc import Callable
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.registry.errors import VersionNotFoundError
from agent_zero.registry.lifecycle import transition
from agent_zero.registry.models import AgentVersion, VersionStatus
from agent_zero.registry.projection import to_read
from agent_zero.registry.repository import RegistryRepository
from agent_zero.registry.schemas import AgentVersionRead
from agent_zero.shared.clock import utc_now


class ApprovalService:
    def __init__(self, db: AsyncSession, clock: Callable[[], datetime] = utc_now) -> None:
        self._db = db
        self._clock = clock

    async def _load(self, agent_id: str, version: str) -> AgentVersion:
        row = await RegistryRepository(self._db).get(agent_id, version)
        if row is None:
            raise VersionNotFoundError(agent_id, version)
        return row

    async def approve(self, agent_id: str, version: str, approved_by: str) -> AgentVersionRead:
        row = await self._load(agent_id, version)
        row.status = transition(row.status, VersionStatus.APPROVED)
        row.approved_by = approved_by
        row.approved_at = self._clock()
        await self._db.commit()
        return to_read(row)

    async def deprecate(self, agent_id: str, version: str) -> AgentVersionRead:
        row = await self._load(agent_id, version)
        row.status = transition(row.status, VersionStatus.DEPRECATED)
        row.deprecated_at = self._clock()
        await self._db.commit()
        return to_read(row)
