from agent_zero.events.broker import EventBroker
from agent_zero.events.models import EventType
from agent_zero.events.schemas import EventDraft


def test_publish_assigns_monotonic_ids() -> None:
    broker = EventBroker()

    first = broker.publish(EventDraft(type=EventType.ATTEMPT_QUEUED))
    second = broker.publish(EventDraft(type=EventType.ATTEMPT_STARTED))

    assert (first.id, second.id) == (1, 2)


async def test_subscriber_receives_live_events() -> None:
    broker = EventBroker()

    async with broker.subscribe() as queue:
        published = broker.publish(EventDraft(type=EventType.FINDING_OPENED))
        received = queue.get_nowait()

    assert received == published


async def test_resubscription_replays_only_missed_events() -> None:
    broker = EventBroker()
    for _ in range(3):
        broker.publish(EventDraft(type=EventType.ATTEMPT_QUEUED))

    async with broker.subscribe(after_id=1) as queue:
        replayed = [queue.get_nowait().id for _ in range(queue.qsize())]

    assert replayed == [2, 3]


async def test_unsubscribed_queue_stops_receiving() -> None:
    broker = EventBroker()
    async with broker.subscribe() as queue:
        pass

    broker.publish(EventDraft(type=EventType.ATTEMPT_QUEUED))

    assert queue.empty()
