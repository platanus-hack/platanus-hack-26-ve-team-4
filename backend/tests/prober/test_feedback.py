from datetime import UTC, datetime

from agent_zero.attempts.models import Attempt, AttemptOutcome, AttemptStatus
from agent_zero.events.models import EventType
from agent_zero.events.schemas import TraceEvent
from agent_zero.prober.feedback import SignalKind, signal_from
from agent_zero.routing.models import Route

NOW = datetime(2026, 10, 24, tzinfo=UTC)


def _attempt(
    outcome: AttemptOutcome | None, assessment: dict[str, object] | None = None
) -> Attempt:
    return Attempt(
        id="attempt-1",
        session_id="sess-1",
        policy_version=0,
        route=Route.PROTECTED,
        run_id="run-1",
        idempotency_key="key",
        messages=["x"],
        customer_id="cust-ana",
        status=AttemptStatus.EVALUATED,
        outcome=outcome,
        assessment=assessment or {},
        created_at=NOW,
        updated_at=NOW,
    )


def _event(kind: EventType, **data: object) -> TraceEvent:
    return TraceEvent(id=1, type=kind, timestamp=NOW, data=dict(data))


def test_violation_carries_the_violated_objectives() -> None:
    attempt = _attempt(
        AttemptOutcome.CONFIRMED_VIOLATION,
        {
            "verdicts": [
                {"objective_id": "OBJ-ORDER", "violated": False},
                {"objective_id": "OBJ-REFUND", "violated": True},
            ]
        },
    )

    signal = signal_from(attempt, [])

    assert signal.kind is SignalKind.VIOLATION
    assert signal.objectives == ("OBJ-REFUND",)
    assert signal.reward is True


def test_prevented_attempt_reports_the_denying_validator() -> None:
    events = [
        _event(EventType.TOOL_PROPOSED, tool="get_order"),
        _event(EventType.TOOL_DENIED, tool="get_order", validator="order_ownership"),
    ]

    signal = signal_from(_attempt(AttemptOutcome.PREVENTED), events)

    assert signal.kind is SignalKind.VALIDATOR_DENIED
    assert signal.validator == "order_ownership"
    assert signal.reward is False


def test_not_achieved_without_an_action_tool_is_no_tool() -> None:
    events = [_event(EventType.TOOL_PROPOSED, tool="search_knowledge")]

    assert signal_from(_attempt(AttemptOutcome.NOT_ACHIEVED), events).kind is SignalKind.NO_TOOL
    assert signal_from(_attempt(AttemptOutcome.NOT_ACHIEVED), []).kind is SignalKind.NO_TOOL


def test_not_achieved_after_an_action_tool_is_a_plain_miss() -> None:
    events = [_event(EventType.TOOL_PROPOSED, tool="get_order")]

    signal = signal_from(_attempt(AttemptOutcome.NOT_ACHIEVED), events)

    assert signal.kind is SignalKind.NOT_ACHIEVED


def test_inconclusive_and_pending_are_never_a_reward() -> None:
    assert signal_from(_attempt(AttemptOutcome.INCONCLUSIVE), []).kind is SignalKind.INCONCLUSIVE
    assert signal_from(_attempt(None), []).kind is SignalKind.INCONCLUSIVE
