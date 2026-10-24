import secrets

from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.routing.models import Route
from agent_zero.sessions.models import ArenaSession
from agent_zero.sessions.repository import SessionRepository
from agent_zero.sessions.schemas import SessionCreate
from agent_zero.shared.clock import utc_now
from agent_zero.shared.ids import new_id
from agent_zero.victim.fixtures import SYNTHETIC_CUSTOMER_IDS


async def create_session(db: AsyncSession, payload: SessionCreate) -> ArenaSession:
    session = ArenaSession(
        id=new_id("sess"),
        alias=payload.alias.strip(),
        customer_id=secrets.choice(SYNTHETIC_CUSTOMER_IDS),
        route=Route.PROTECTED,
        created_at=utc_now(),
    )
    await SessionRepository(db).add(session)
    await db.commit()
    return session
