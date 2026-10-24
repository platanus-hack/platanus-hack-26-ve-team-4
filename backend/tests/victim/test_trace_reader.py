import json
from datetime import UTC, datetime
from typing import Any, cast

from agent_zero.agent_gateway.business_policy import CallContext
from agent_zero.attempts.models import AttemptOutcome
from agent_zero.events.models import EventType
from agent_zero.events.schemas import TraceEvent
from agent_zero.oracles.assessment_service import AssessmentService
from agent_zero.oracles.trace_reader import tool_evidence
from agent_zero.victim.environments import Environments
from agent_zero.victim.tool_effects import replayed_operation, stored_operation
from agent_zero.victim.trace_observer import trace_data
from agent_zero.victim.trace_schemas import RefundEffect

CONTEXT = CallContext(
    attempt_id="attempt-1",
    session_id="sess-1",
    session_customer_id="cust-ana",
    environment="protected",
    policy_version=0,
    run_id="run-1",
    operation_id="op-1",
)
COMMON = {
    "tool": "request_refund",
    "arguments": {"order_id": "A-1001", "amount": 25},
    "environment": "protected",
    "session_customer_id": "cust-ana",
    "operation_id": "op-1",
}
REFUND_OUTPUT = {
    "approved": True,
    "order_id": "A-1001",
    "customer_id": "cust-ana",
    "amount": 25.0,
    "refunded_total": 30.0,
    "total": 45,
}


def event(data: dict[str, Any], kind: EventType = EventType.TOOL_COMPLETED) -> TraceEvent:
    return TraceEvent(
        id=7,
        timestamp=datetime(2026, 10, 24, tzinfo=UTC),
        type=kind,
        attempt_id="attempt-1",
        session_id="sess-1",
        policy_version=0,
        data=data,
    )


def test_a_v1_event_is_read_with_its_effect_rebuilt_from_the_output() -> None:
    legacy = event(COMMON | {"output": json.dumps(REFUND_OUTPUT)})

    [item] = tool_evidence([legacy])

    assert item.readable
    assert item.effect == {
        "kind": "refund",
        "order_id": "A-1001",
        "owner_customer_id": "cust-ana",
        "amount_cents": 2500,
        "refunded_before_cents": 500,
        "refunded_after_cents": 3000,
        "total_cents": 4500,
    }


def test_a_completed_event_without_effect_or_object_output_is_unreadable() -> None:
    without_effect = event(COMMON | {"schema_version": 2, "output": REFUND_OUTPUT, "effect": None})
    garbled_v1 = event(COMMON | {"output": "no es json"})

    assert [item.readable for item in tool_evidence([without_effect, garbled_v1])] == [False, False]


async def test_an_unreadable_trace_makes_the_attempt_inconclusive() -> None:
    unreadable = event(COMMON | {"schema_version": 2, "output": None, "effect": None})
    # La traza ilegible se rechaza antes de consultar los entornos.
    service = AssessmentService(cast(Environments, None))

    assessment = await service.assess(CONTEXT, [unreadable], "Listo, reembolsado.")

    assert assessment.outcome is AttemptOutcome.INCONCLUSIVE
    assert "request_refund" in assessment.detail


def test_the_observer_writes_an_invalid_effect_as_missing_instead_of_failing() -> None:
    data = trace_data(
        "tool_completed",
        CONTEXT,
        "request_refund",
        {"arguments": {}, "output": json.dumps(REFUND_OUTPUT), "effect": {"kind": "teleport"}},
    ).model_dump(mode="json")

    assert data["output"] == REFUND_OUTPUT
    assert data["effect"] is None


def test_a_replayed_operation_returns_the_same_text_and_effect() -> None:
    effect = RefundEffect(
        order_id="A-1001",
        owner_customer_id="cust-ana",
        amount_cents=2500,
        refunded_before_cents=500,
        refunded_after_cents=3000,
        total_cents=4500,
    )

    replayed = replayed_operation(stored_operation(REFUND_OUTPUT, effect))
    legacy = replayed_operation(json.dumps(REFUND_OUTPUT))

    assert json.loads(replayed.text) == REFUND_OUTPUT
    assert replayed.effect == effect.model_dump(mode="json")
    assert legacy.effect is None
