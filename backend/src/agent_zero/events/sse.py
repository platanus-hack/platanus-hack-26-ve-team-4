import asyncio
from collections.abc import AsyncGenerator

from agent_zero.events.broker import EventBroker
from agent_zero.events.models import Visibility
from agent_zero.events.public_projection import public_projection
from agent_zero.events.schemas import TraceEvent

HEARTBEAT = ": ping\n\n"


def format_sse(event: TraceEvent) -> str:
    return f"id: {event.id}\nevent: {event.type.value}\ndata: {event.model_dump_json()}\n\n"


async def public_stream(
    broker: EventBroker, after_id: int | None, heartbeat_seconds: float = 15.0
) -> AsyncGenerator[str]:
    async with broker.subscribe(after_id) as queue:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=heartbeat_seconds)
            except TimeoutError:
                yield HEARTBEAT
                continue
            if event.visibility is Visibility.PUBLIC:
                yield format_sse(public_projection(event))
