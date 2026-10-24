from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.sessions.models import ArenaSession


class SessionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def add(self, session: ArenaSession) -> ArenaSession:
        self._db.add(session)
        await self._db.flush()
        return session

    async def get(self, session_id: str) -> ArenaSession | None:
        return await self._db.get(ArenaSession, session_id)
