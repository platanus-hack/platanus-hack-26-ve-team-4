from collections.abc import Sequence

from sqlalchemy import select
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

    async def list_all(self) -> Sequence[ArenaSession]:
        result = await self._db.scalars(select(ArenaSession).order_by(ArenaSession.created_at))
        return result.all()
