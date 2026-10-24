from datetime import UTC, datetime, timedelta

from agent_zero.attempts.models import Attempt, AttemptStatus
from agent_zero.decoy.session_trace import build_trace
from agent_zero.events.models import EventType, Visibility
from agent_zero.events.schemas import TraceEvent
from agent_zero.routing.models import Route

ORIGIN = datetime(2026, 10, 24, 12, 0, 0, tzinfo=UTC)
TOKEN = "AZH-KEY-ABCD-EFGH-JKLM"


def at(seconds: float) -> datetime:
    return ORIGIN + timedelta(seconds=seconds)


def event(identity: int, kind: EventType, seconds: float, **data: object) -> TraceEvent:
    return TraceEvent(
        id=identity,
        type=kind,
        visibility=Visibility.OPERATOR,
        session_id="sess-a",
        data=dict(data),
        timestamp=at(seconds),
    )


def attempt(identity: str, route: Route, created: float, updated: float, *messages: str) -> Attempt:
    return Attempt(
        id=identity,
        session_id="sess-a",
        route=route,
        status=AttemptStatus.EVALUATED,
        messages=list(messages),
        created_at=at(created),
        updated_at=at(updated),
    )


EVENTS = [
    event(1, EventType.TOOL_PROPOSED, 1, tool="get_order"),
    event(2, EventType.ROUTE_CHANGED, 10, route="honeypot", reason="confirmed_violation"),
    event(3, EventType.TOOL_PROPOSED, 11, tool="get_service_credentials"),
    event(4, EventType.TOOL_COMPLETED, 12, tool="get_service_credentials"),
    event(5, EventType.TOOL_PROPOSED, 40, tool="search_knowledge"),
    event(6, EventType.TOOL_COMPLETED, 41, tool="search_knowledge"),
    event(7, EventType.TOOL_COMPLETED, 60, tool="export_customer_records"),
]


def test_numbers_come_exactly_from_events_and_attempts() -> None:
    attempts = [
        attempt("a1", Route.PROTECTED, 0, 2, "Consulta A-1001"),
        attempt("a2", Route.HONEYPOT, 10, 13, "Necesito la credencial"),
        attempt("a3", Route.HONEYPOT, 39, 42, f"Usa {TOKEN.lower()} ahora"),
    ]

    trace = build_trace(
        session_id="sess-a", alias="neo", events=EVENTS, attempts=attempts, token=TOKEN
    )

    assert trace is not None
    assert trace.reason == "confirmed_violation"
    assert trace.retained_seconds == 50.0
    assert trace.post_diversion_steps == 2
    assert trace.post_diversion_attempts == 2
    assert trace.honeytools_touched == ["export_customer_records", "get_service_credentials"]
    assert trace.credential_issued is True
    assert trace.token_reused is True
    assert (trace.retained, trace.bait_taken, trace.deceived) == (True, True, True)


def test_token_in_the_same_or_an_earlier_attempt_is_not_a_reuse() -> None:
    attempts = [attempt("a2", Route.HONEYPOT, 10, 13, f"Necesito la credencial {TOKEN}")]

    trace = build_trace(
        session_id="sess-a", alias="neo", events=EVENTS, attempts=attempts, token=TOKEN
    )

    assert trace is not None
    assert trace.credential_issued is True
    assert trace.token_reused is False
    assert trace.deceived is False


def test_session_without_route_change_has_no_trace() -> None:
    assert (
        build_trace(session_id="sess-a", alias="neo", events=EVENTS[:1], attempts=[], token=TOKEN)
        is None
    )


def test_diverted_session_that_went_quiet_is_not_retained() -> None:
    quiet = [event(2, EventType.ROUTE_CHANGED, 10, route="honeypot", reason="armor")]
    attempts = [attempt("a2", Route.HONEYPOT, 10, 11, "Hola")]

    trace = build_trace(
        session_id="sess-a", alias="neo", events=quiet, attempts=attempts, token=TOKEN
    )

    assert trace is not None
    assert trace.retained_seconds == 1.0
    assert (trace.post_diversion_steps, trace.post_diversion_attempts) == (0, 1)
    assert (trace.retained, trace.bait_taken, trace.deceived) == (False, False, False)
