from typing import Annotated

from fastapi import APIRouter, Header
from fastapi.responses import StreamingResponse

from agent_zero.events.sse import public_stream
from agent_zero.shared.dependencies import Broker

router = APIRouter(prefix="/api/arena", tags=["arena"])


@router.get("/events")
async def stream_events(
    broker: Broker, last_event_id: Annotated[int | None, Header()] = None
) -> StreamingResponse:
    return StreamingResponse(
        public_stream(broker, last_event_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
