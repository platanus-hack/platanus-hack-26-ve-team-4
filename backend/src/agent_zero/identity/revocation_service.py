from collections.abc import Callable
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.identity.models import RevokedAgent, RevokedCredential
from agent_zero.identity.repository import RevocationRepository
from agent_zero.identity.schemas import AgentPrincipal
from agent_zero.shared.clock import utc_now


class RevocationService:
    def __init__(self, db: AsyncSession, clock: Callable[[], datetime] = utc_now) -> None:
        self._db = db
        self._clock = clock
        self._repository = RevocationRepository(db)

    async def revoke_credential(self, credential_id: str) -> None:
        await self._repository.add_credential(
            RevokedCredential(credential_id=credential_id, revoked_at=self._clock())
        )
        await self._db.commit()

    async def revoke_agent(self, agent_id: str, version: str | None = None) -> None:
        await self._repository.add_agent(
            RevokedAgent(agent_id=agent_id, version=version, revoked_at=self._clock())
        )
        await self._db.commit()

    async def is_revoked(self, principal: AgentPrincipal) -> bool:
        if await self._repository.credential_is_revoked(principal.credential_id):
            return True
        return await self._repository.agent_is_revoked(principal.agent_id, principal.version)
