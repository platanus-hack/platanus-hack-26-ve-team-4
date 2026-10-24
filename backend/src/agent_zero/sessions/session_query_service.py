from collections.abc import Collection

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.routing.models import Route
from agent_zero.sessions.models import ArenaSession
from agent_zero.sessions.repository import SessionRepository
from agent_zero.shared.clock import utc_now
from agent_zero.shared.ids import new_id


async def query_session(db: AsyncSession, session_id: str) -> ArenaSession | None:
    return await SessionRepository(db).get(session_id)


async def session_aliases(db: AsyncSession, session_ids: Collection[str]) -> dict[str, str]:
    if not session_ids:
        return {}
    rows = await db.execute(
        select(ArenaSession.id, ArenaSession.alias).where(ArenaSession.id.in_(session_ids))
    )
    return {session_id: alias for session_id, alias in rows}


async def divert_session(db: AsyncSession, session_id: str) -> bool:
    return await SessionRepository(db).divert(session_id)


async def internal_session(db: AsyncSession, customer_id: str, alias: str) -> ArenaSession:
    session = ArenaSession(
        id=new_id("internal"),
        alias=alias,
        customer_id=customer_id,
        route=Route.PROTECTED,
        created_at=utc_now(),
    )
    await SessionRepository(db).add(session)
    await db.commit()
    return session
