import secrets
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.arena.models import ArenaState
from agent_zero.arena.transactions import serialize_write
from agent_zero.armor.model_armor import ModelArmor
from agent_zero.routing.models import Route
from agent_zero.sessions.models import ArenaSession
from agent_zero.sessions.repository import SessionRepository
from agent_zero.sessions.reserved_alias import is_reserved_alias
from agent_zero.sessions.schemas import SessionCreate
from agent_zero.shared.clock import utc_now
from agent_zero.shared.ids import new_id
from agent_zero.victim.fixtures import customer_ids

RESERVED_ALIAS = (
    "Los alias que empiezan con «Agente-» o «Interno-» están reservados para el equipo."
)


async def create_session(
    db: AsyncSession,
    payload: SessionCreate,
    limit: int = 3,
    *,
    provision: Callable[[str], Awaitable[None]] | None = None,
    operator: bool = False,
) -> ArenaSession:
    if not operator and is_reserved_alias(payload.alias):
        raise ValueError(RESERVED_ALIAS)
    await serialize_write(db)
    state = await db.get(ArenaState, 1)
    if state is not None and not state.accepting:
        raise ValueError("Las entradas de la ronda están cerradas.")
    allocated = await SessionRepository(db).allocated_customers()
    available = [customer for customer in customer_ids(limit) if customer not in allocated]
    if not available or len(allocated) >= limit:
        raise ValueError("Se agotaron las identidades sintéticas de esta ronda.")
    alias = ModelArmor().redact_pii(payload.alias.strip())
    if not operator and is_reserved_alias(alias):
        raise ValueError(RESERVED_ALIAS)
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
    if provision is not None:
        await provision(session.customer_id)
    await SessionRepository(db).add(session)
    await db.commit()
    return session
