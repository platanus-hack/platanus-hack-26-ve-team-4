from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.identity.schemas import AgentGrant
from agent_zero.registry.discovery_service import DiscoveryService


async def grant_for(db: AsyncSession, agent_id: str, version: str) -> AgentGrant:
    approved = await DiscoveryService(db).resolve(agent_id, version)
    manifest = approved.manifest
    return AgentGrant(
        agent_id=manifest.agent_id,
        version=manifest.version,
        department=manifest.department,
        scopes=manifest.scopes,
        clearance=manifest.max_classification,
        allowed_regions=manifest.allowed_regions,
    )
