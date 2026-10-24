import asyncio
from collections import deque
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from agent_zero.events.schemas import EventDraft, TraceEvent
from agent_zero.shared.clock import utc_now


class EventBroker:
    def __init__(self, history_size: int = 500) -> None:
        self._history: deque[TraceEvent] = deque(maxlen=history_size)
        self._subscribers: set[asyncio.Queue[TraceEvent]] = set()
        self._next_id = 1
        self._history_source: Callable[[int], Awaitable[list[TraceEvent]]] | None = None

    def set_history_source(self, source: Callable[[int], Awaitable[list[TraceEvent]]]) -> None:
        self._history_source = source

    def publish(self, draft: EventDraft) -> TraceEvent:
        event = TraceEvent(id=self._next_id, timestamp=utc_now(), **draft.model_dump())
        self.publish_event(event)
        return event

    def publish_event(self, event: TraceEvent) -> None:
        self._next_id = max(self._next_id, event.id + 1)
        self._history.append(event)
        for queue in self._subscribers:
            queue.put_nowait(event)

    @asynccontextmanager
    async def subscribe(
        self, after_id: int | None = None
    ) -> AsyncIterator[asyncio.Queue[TraceEvent]]:
        queue: asyncio.Queue[TraceEvent] = asyncio.Queue()
        self._subscribers.add(queue)
        try:
            if after_id is not None:
                replay = (
                    await self._history_source(after_id)
                    if self._history_source is not None
                    else [event for event in self._history if event.id > after_id]
                )
                arrivals = []
                while not queue.empty():
                    arrivals.append(queue.get_nowait())
                unique = {event.id: event for event in [*replay, *arrivals] if event.id > after_id}
                for event in sorted(unique.values(), key=lambda item: item.id):
                    queue.put_nowait(event)
            yield queue
        finally:
            self._subscribers.discard(queue)
