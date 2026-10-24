import secrets

from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.armor.model_armor import ModelArmor
from agent_zero.routing.models import Route
from agent_zero.sessions.models import ArenaSession
from agent_zero.sessions.repository import SessionRepository
from agent_zero.sessions.schemas import SessionCreate
from agent_zero.shared.clock import utc_now
from agent_zero.shared.ids import new_id
from agent_zero.victim.fixtures import SYNTHETIC_CUSTOMER_IDS


async def create_session(db: AsyncSession, payload: SessionCreate, limit: int = 3) -> ArenaSession:
    allocated = await SessionRepository(db).allocated_customers()
    available = [customer for customer in SYNTHETIC_CUSTOMER_IDS if customer not in allocated]
    if not available or len(allocated) >= limit:
        raise ValueError("Se agotaron las identidades sintéticas de esta ronda.")
    alias = ModelArmor().redact_pii(payload.alias.strip())
    if await SessionRepository(db).alias_exists(alias):
        raise ValueError("Este alias ya está en uso.")
    if len(alias) < 2 or len(alias) > 40:
        raise ValueError("El alias debe tener entre 2 y 40 caracteres.")
    session = ArenaSession(
        id=new_id("sess"),
        alias=alias,
        customer_id=secrets.choice(available),
        route=Route.PROTECTED,
        created_at=utc_now(),
    )
    await SessionRepository(db).add(session)
    await db.commit()
    return session
