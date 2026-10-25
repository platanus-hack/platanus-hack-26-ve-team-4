from datetime import timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.events.event_store import EventStore
from agent_zero.events.models import EventType
from agent_zero.routing.session_risk import ToolOutcome, risk_score
from agent_zero.sessions.models import ArenaSession
from agent_zero.shared.clock import utc_now
from agent_zero.victim.fixtures import orders_for_customer


def _outcome(kind: EventType, data: dict[str, Any]) -> ToolOutcome:
    arguments = data.get("arguments")
    order_id = arguments.get("order_id") if isinstance(arguments, dict) else None
    validator = data.get("validator")
    return ToolOutcome(
        tool=str(data.get("tool", "")),
        denied=kind is EventType.TOOL_DENIED,
        validator=validator if isinstance(validator, str) else None,
        order_id=order_id if isinstance(order_id, str) else None,
    )


async def session_risk(
    events: EventStore, session: ArenaSession, window_seconds: float, db: AsyncSession
) -> int:
    since = utc_now() - timedelta(seconds=window_seconds)
    rows = await events.tool_outcomes(session.id, since, db)
    try:
        own = [order.order_id for order in orders_for_customer(session.customer_id)]
    except ValueError:
        own = []
    return risk_score([_outcome(kind, data) for kind, data in rows], own)
