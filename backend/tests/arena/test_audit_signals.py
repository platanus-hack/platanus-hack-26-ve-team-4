from typing import Any

from agent_zero.arena.audit_signals import denial_info, family_map, session_risk
from agent_zero.events.models import EventType

OWNER_VALIDATOR = "order_belongs_to_session_customer"


def event(event_id: int, kind: EventType, data: dict[str, Any] | None) -> dict[str, Any]:
    return {"id": event_id, "type": kind.value, "data": data}


def test_denial_info_keeps_stage_reason_and_detail_of_denied_steps() -> None:
    events = [
        event(1, EventType.TOOL_COMPLETED, {"tool": "get_order", "output": {}}),
        event(
            2,
            EventType.TOOL_DENIED,
            {"tool": "get_order", "stage": "input", "reason": "input_blocked", "detail": "Hola"},
        ),
        event(3, EventType.TOOL_DENIED, None),
    ]

    assert denial_info(events) == {
        2: {"stage": "input", "reason": "input_blocked", "detail": "Hola"},
        3: {"stage": "", "reason": "", "detail": ""},
    }


def test_family_map_reads_only_cases_with_attempt_and_family() -> None:
    rows: list[dict[str, Any]] = [
        {"attempt_id": "att-1", "case_json": {"family": "familia-a"}},
        {"attempt_id": None, "case_json": {"family": "familia-b"}},
        {"attempt_id": "att-2", "case_json": {}},
    ]

    assert family_map(rows) == {"att-1": "familia-a"}


def test_session_risk_scores_order_owner_denials() -> None:
    events = [
        event(
            7,
            EventType.TOOL_DENIED,
            {
                "tool": "request_refund",
                "validator": OWNER_VALIDATOR,
                "arguments": {"order_id": "ORD-9"},
            },
        ),
        event(8, EventType.TOOL_COMPLETED, {"tool": "get_order", "arguments": {}}),
    ]

    score, signals = session_risk(events, "cliente-desconocido")

    assert score > 0
    assert signals == [{"validator": OWNER_VALIDATOR, "count": 1}]


def test_session_risk_without_events_is_zero() -> None:
    assert session_risk([], "cliente-desconocido") == (0, [])
