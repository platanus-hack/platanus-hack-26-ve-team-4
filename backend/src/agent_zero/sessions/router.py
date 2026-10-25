from datetime import UTC, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, status

from agent_zero.arena.dependencies import Core
from agent_zero.policies.validator_catalog import OBJECTIVE_CONTROLS
from agent_zero.registry.dependencies import OperatorFlag
from agent_zero.sessions.dependencies import CurrentSession
from agent_zero.sessions.schemas import SessionCreate, SessionIssued
from agent_zero.sessions.session_creation_service import create_session
from agent_zero.sessions.session_token import SessionTokens
from agent_zero.shared.dependencies import DbSession
from agent_zero.victim.fixtures import orders_for_customer

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create(
    payload: SessionCreate, db: DbSession, core: Core, operator: OperatorFlag
) -> SessionIssued:
    await core.ensure_agents()
    async with core.admission_lock:
        try:
            session = await create_session(
                db,
                payload,
                core.fleet.settings.arena_session_limit,
                provision=core.environments.ensure_customer,
                operator=operator,
            )
        except ValueError as error:
            raise HTTPException(409, str(error)) from error
    created_at = session.created_at.replace(tzinfo=UTC)
    expires_at = created_at + timedelta(seconds=core.fleet.settings.arena_session_ttl_seconds)
    return SessionIssued(
        id=session.id,
        alias=session.alias,
        created_at=created_at,
        token=SessionTokens(core.fleet.settings).issue(session.id, expires_at),
        expires_at=expires_at,
        customer_name=session.customer_id.removeprefix("cust-").title(),
        order_ids=[order.order_id for order in orders_for_customer(session.customer_id)],
        objectives=list(OBJECTIVE_CONTROLS),
        limits={
            "attempts_per_minute": core.fleet.settings.arena_attempts_per_minute,
            "max_messages": 4,
            "message_max_length": 4000,
        },
    )


@router.get("/me")
async def me(session: CurrentSession, core: Core) -> dict[str, Any]:
    created_at = session.created_at.replace(tzinfo=UTC)
    settings = core.fleet.settings
    return {
        "id": session.id,
        "alias": session.alias,
        "created_at": created_at.isoformat(),
        "expires_at": (
            created_at + timedelta(seconds=settings.arena_session_ttl_seconds)
        ).isoformat(),
        "customer_name": session.customer_id.removeprefix("cust-").title(),
        "order_ids": [order.order_id for order in orders_for_customer(session.customer_id)],
        "objectives": list(OBJECTIVE_CONTROLS),
        "limits": {
            "attempts_per_minute": settings.arena_attempts_per_minute,
            "max_messages": 4,
            "message_max_length": 4000,
        },
    }
