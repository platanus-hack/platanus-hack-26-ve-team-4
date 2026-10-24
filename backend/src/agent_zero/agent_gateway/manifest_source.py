from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agent_zero.registry.discovery_service import DiscoveryService
from agent_zero.registry.errors import RegistryError
from agent_zero.registry.schemas import ToolGrant


class ManifestSource(Protocol):
    async def tool_grants(self, agent_id: str, version: str) -> dict[str, ToolGrant] | None: ...


class RegistryManifestSource:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def tool_grants(self, agent_id: str, version: str) -> dict[str, ToolGrant] | None:
        async with self._sessions() as db:
            try:
                approved = await DiscoveryService(db).resolve(agent_id, version)
            except RegistryError:
                return None
        return {tool.name: tool for tool in approved.manifest.tools}
