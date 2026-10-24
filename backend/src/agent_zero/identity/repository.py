from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.identity.models import RevokedAgent, RevokedCredential


class RevocationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def add_credential(self, revoked: RevokedCredential) -> None:
        if await self._db.get(RevokedCredential, revoked.credential_id) is None:
            self._db.add(revoked)
            await self._db.flush()

    async def add_agent(self, revoked: RevokedAgent) -> None:
        self._db.add(revoked)
        await self._db.flush()

    async def credential_is_revoked(self, credential_id: str) -> bool:
        return await self._db.get(RevokedCredential, credential_id) is not None

    async def agent_is_revoked(self, agent_id: str, version: str) -> bool:
        statement = (
            select(RevokedAgent.id)
            .where(
                RevokedAgent.agent_id == agent_id,
                or_(RevokedAgent.version.is_(None), RevokedAgent.version == version),
            )
            .limit(1)
        )
        return (await self._db.execute(statement)).first() is not None
