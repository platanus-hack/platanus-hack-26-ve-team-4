from datetime import UTC, datetime

from agent_zero.events.models import EventType
from agent_zero.events.schemas import TraceEvent
from agent_zero.patches.integrity_probe import integrity_probe, untrusted_effects


def event(tool: str, provenance: dict[str, str]) -> TraceEvent:
    return TraceEvent(
        id=1,
        timestamp=datetime.now(UTC),
        type=EventType.TOOL_COMPLETED,
        data={"tool": tool, "provenance": provenance},
    )


def test_probe_injects_an_in_limit_refund_for_order_and_refund_objectives() -> None:
    probe = integrity_probe("OBJ-REFUND", "cust-ana")
    assert probe is not None
    assert "amount 10" in probe.fixtures[0].content
    assert probe.case.adversarial is True
    assert integrity_probe("OBJ-MEMORY", "cust-ana") is None


def test_counts_only_effects_driven_by_low_integrity_arguments() -> None:
    events = [
        event("request_refund", {"amount": "untrusted"}),
        event("request_refund", {"amount": "user"}),
        event("search_knowledge", {"query": "untrusted"}),
    ]
    assert untrusted_effects(events) == 1
