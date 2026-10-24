import asyncio
from collections.abc import AsyncGenerator
from contextlib import suppress

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
    cursor = after_id if after_id is not None else broker.latest_id
    loop = asyncio.get_running_loop()
    next_heartbeat = loop.time() + heartbeat_seconds
    async with broker.subscribe(after_id) as queue:
        while True:
            with suppress(TimeoutError):
                await asyncio.wait_for(queue.get(), timeout=min(heartbeat_seconds, 1.0))
            # Another process may have committed and dispatched an event without
            # touching this broker. Read the log on wake-up and periodic polling;
            # a local higher ID must never skip an unseen lower public ID.
            for event in await broker.read_after(cursor):
                if event.id > cursor and event.visibility is Visibility.PUBLIC:
                    cursor = event.id
                    yield format_sse(public_projection(event))
                    next_heartbeat = loop.time() + heartbeat_seconds
            if loop.time() >= next_heartbeat:
                yield HEARTBEAT
                next_heartbeat = loop.time() + heartbeat_seconds
