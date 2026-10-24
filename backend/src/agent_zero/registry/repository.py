from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.registry.models import AgentVersion, VersionStatus


class RegistryRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def add(self, row: AgentVersion) -> AgentVersion:
        self._db.add(row)
        await self._db.flush()
        return row

    async def get(self, agent_id: str, version: str) -> AgentVersion | None:
        return await self._db.get(AgentVersion, (agent_id, version))

    async def list_by_status(self, status: VersionStatus) -> list[AgentVersion]:
        result = await self._db.execute(select(AgentVersion).where(AgentVersion.status == status))
        return list(result.scalars())

    async def list_for_agent(
        self, agent_id: str, status: VersionStatus | None = None
    ) -> list[AgentVersion]:
        query = select(AgentVersion).where(AgentVersion.agent_id == agent_id)
        if status is not None:
            query = query.where(AgentVersion.status == status)
        result = await self._db.execute(query)
        return list(result.scalars())
