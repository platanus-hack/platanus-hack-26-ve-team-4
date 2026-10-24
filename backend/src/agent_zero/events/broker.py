import asyncio
from collections import deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from agent_zero.events.schemas import EventDraft, TraceEvent
from agent_zero.shared.clock import utc_now


class EventBroker:
    def __init__(self, history_size: int = 500) -> None:
        self._history: deque[TraceEvent] = deque(maxlen=history_size)
        self._subscribers: set[asyncio.Queue[TraceEvent]] = set()
        self._next_id = 1

    def publish(self, draft: EventDraft) -> TraceEvent:
        event = TraceEvent(id=self._next_id, timestamp=utc_now(), **draft.model_dump())
        self._next_id += 1
        self._history.append(event)
        for queue in self._subscribers:
            queue.put_nowait(event)
        return event

    @asynccontextmanager
    async def subscribe(
        self, after_id: int | None = None
    ) -> AsyncIterator[asyncio.Queue[TraceEvent]]:
        queue: asyncio.Queue[TraceEvent] = asyncio.Queue()
        if after_id is not None:
            for event in self._history:
                if event.id > after_id:
                    queue.put_nowait(event)
        self._subscribers.add(queue)
        try:
            yield queue
        finally:
            self._subscribers.discard(queue)
