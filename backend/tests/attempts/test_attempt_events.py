from datetime import UTC, datetime

from agent_zero.attempts.attempt_events import AttemptEvents
from agent_zero.attempts.models import (
    Attempt,
    AttemptOrigin,
    AttemptOutcome,
    AttemptStatus,
)
from agent_zero.events.broker import EventBroker
from agent_zero.events.models import EventType, Visibility
from agent_zero.events.schemas import TraceEvent
from agent_zero.routing.models import Route

NOW = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)


def _attempt() -> Attempt:
    return Attempt(
        id="attempt-1",
        session_id="sess-1",
        origin=AttemptOrigin.AUDIENCE,
        idempotency_key="clave-0001",
        messages=["hola"],
        policy_version=2,
        route=Route.HONEYPOT,
        run_id="run-1",
        status=AttemptStatus.QUEUED,
        created_at=NOW,
        updated_at=NOW,
    )


async def _published(broker: EventBroker) -> list[TraceEvent]:
    async with broker.subscribe(after_id=0) as queue:
        return [queue.get_nowait() for _ in range(queue.qsize())]


async def test_every_transition_is_published_for_operator_and_public() -> None:
    broker = EventBroker()
    events = AttemptEvents(broker)
    attempt = _attempt()

    events.queued(attempt)
    attempt.status = AttemptStatus.RUNNING
    events.started(attempt)
    attempt.status, attempt.outcome = AttemptStatus.EVALUATED, AttemptOutcome.CONTAINED_HONEYPOT
    events.finished(attempt)

    published = await _published(broker)
    kinds = [event.type for event in published if event.visibility is Visibility.PUBLIC]
    assert kinds == [
        EventType.ATTEMPT_QUEUED,
        EventType.ATTEMPT_STARTED,
        EventType.ATTEMPT_EVALUATED,
    ]
    assert len(published) == 6


async def test_public_events_carry_no_identifiers_route_or_real_outcome() -> None:
    broker = EventBroker()
    attempt = _attempt()
    attempt.status, attempt.outcome = AttemptStatus.EVALUATED, AttemptOutcome.CONTAINED_HONEYPOT
    AttemptEvents(broker).finished(attempt)

    operator, public = await _published(broker)

    assert operator.attempt_id == "attempt-1"
    assert operator.data["outcome"] == "contained_honeypot"
    assert public.attempt_id is None
    assert public.session_id is None
    assert public.data == {"status": "evaluated", "outcome": "apparent_success"}
    assert "honeypot" not in public.model_dump_json()
