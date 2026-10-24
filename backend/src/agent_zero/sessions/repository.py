from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.routing.models import Route
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

    async def allocated_customers(self) -> set[str]:
        return set(
            await self._db.scalars(
                select(ArenaSession.customer_id).where(ArenaSession.id.startswith("sess-"))
            )
        )

    async def alias_exists(self, alias: str) -> bool:
        return (
            await self._db.scalar(
                select(ArenaSession.id)
                .where(
                    func.lower(ArenaSession.alias) == alias.lower(),
                    ArenaSession.id.startswith("sess-"),
                )
                .limit(1)
            )
            is not None
        )

    async def divert(self, session_id: str) -> bool:
        session = await self.get(session_id)
        if session is None or session.route is Route.HONEYPOT:
            return False
        session.route = Route.HONEYPOT
        await self._db.commit()
        return True
