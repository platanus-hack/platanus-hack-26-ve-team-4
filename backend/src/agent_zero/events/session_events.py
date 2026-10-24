from collections import defaultdict
from collections.abc import Collection

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.events.event_delivery import to_trace
from agent_zero.events.models import EventRecord, EventType, Visibility
from agent_zero.events.schemas import TraceEvent


async def events_for_sessions(
    db: AsyncSession, session_ids: Collection[str], types: Collection[EventType]
) -> dict[str, list[TraceEvent]]:
    grouped: dict[str, list[TraceEvent]] = defaultdict(list)
    if not session_ids:
        return grouped
    rows = await db.scalars(
        select(EventRecord)
        .where(
            EventRecord.session_id.in_(list(session_ids)),
            EventRecord.visibility == Visibility.OPERATOR,
            EventRecord.type.in_(list(types)),
        )
        .order_by(EventRecord.id)
    )
    for row in rows:
        if row.session_id is not None:
            grouped[row.session_id].append(to_trace(row))
    return grouped
