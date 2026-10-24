from agent_zero.events.broker import EventBroker
from agent_zero.events.models import EventType, Visibility
from agent_zero.events.schemas import EventDraft
from agent_zero.events.sse import HEARTBEAT, format_sse, public_stream


def test_format_sse_includes_id_and_type() -> None:
    event = EventBroker().publish(EventDraft(type=EventType.POLICY_ACTIVATED))

    frame = format_sse(event)

    assert frame.startswith("id: 1\nevent: policy_activated\ndata: {")
    assert frame.endswith("\n\n")


async def test_public_stream_hides_operator_events() -> None:
    broker = EventBroker()
    broker.publish(EventDraft(type=EventType.ROUTE_CHANGED, visibility=Visibility.OPERATOR))
    broker.publish(EventDraft(type=EventType.ATTEMPT_QUEUED, visibility=Visibility.PUBLIC))

    stream = public_stream(broker, after_id=0, heartbeat_seconds=0.01)
    first = await anext(stream)
    second = await anext(stream)
    await stream.aclose()

    assert "event: attempt_queued" in first
    assert second == HEARTBEAT
