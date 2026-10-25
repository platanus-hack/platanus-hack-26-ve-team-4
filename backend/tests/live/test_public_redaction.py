import json
from typing import Any

from agent_zero.attempts.models import Attempt, AttemptOutcome
from agent_zero.live.models import LiveBoard, LiveDenial
from agent_zero.live.redaction import redact_live
from agent_zero.live.service import BoardData, _denial, build_board, denial_control
from agent_zero.routing.models import Route
from agent_zero.sessions.models import ArenaSession
from tests.live.support import attempt, session

CANARY_HONEYPOT = "AZH_0123456789abcdef_A-1001"
CANARY_PROTECTED = "AZP_0123456789abcdef_B-2002"
HONEYTOKEN = "AZH-KEY-ABCD-EFGH-JKLM"
RULE_VALIDATOR = "flow:cupo-diario"

ATTEMPT_KEYS = {
    "id",
    "number",
    "status",
    "outcome",
    "route",
    "policy_version",
    "messages",
    "reply",
    "denials",
    "violated_objectives",
    "patched_by",
    "technique",
    "created_at",
    "updated_at",
}
DENIAL_KEYS = {"tool", "reason", "control"}


def leaking_board() -> tuple[LiveBoard, dict[str, Any]]:
    reply = (
        f"Referencia interna {CANARY_HONEYPOT}, canario {CANARY_PROTECTED} y clave {HONEYTOKEN}."
    )
    row: Attempt = attempt(
        "p1",
        "sess-pub",
        seconds=10,
        outcome=AttemptOutcome.CONTAINED_HONEYPOT,
        route=Route.HONEYPOT,
        reply=reply,
    )
    row.messages = [f"Mi clave es {HONEYTOKEN}."]
    sessions: list[ArenaSession] = [session("sess-pub", "neo", Route.HONEYPOT)]
    denials = {
        "p1": [
            LiveDenial(tool="get_order", reason="rate_limited", control=None),
            _denial(
                {"tool": "get_order", "reason": "business_rule_denied", "validator": RULE_VALIDATOR}
            ),
        ]
    }
    data = BoardData([row], sessions, [], [], [], denials, {})
    board = build_board(data, revealed=False, llm_mode="demo", limit=6, accepting=True)
    return board, json.loads(board.model_dump_json())


def test_redact_live_removes_canaries_and_honeytokens() -> None:
    text = f"A {CANARY_HONEYPOT} B {CANARY_PROTECTED} C {HONEYTOKEN} D"

    assert redact_live(text) == "A [referencia] B [referencia] C [referencia] D"


def test_the_public_board_never_leaks_internal_references_before_the_reveal() -> None:
    board, payload = leaking_board()
    dumped = board.model_dump_json()

    leaked_values = (CANARY_PROTECTED, "AZP_", "AZH_", "AZH-KEY", "arguments", "validator")
    for leaked in (*leaked_values, RULE_VALIDATOR, "flow:"):
        assert leaked not in dumped
    for word in ("args", "trace"):
        assert word not in dumped

    item = payload["sessions"][0]["attempts"][0]
    assert item["outcome"] == "contained_honeypot"
    assert item["route"] == "honeypot"
    assert "[referencia]" in item["reply"]
    assert item["messages"] == ["Mi clave es [referencia]."]
    assert item["denials"] == [
        {"tool": "get_order", "reason": "rate_limited", "control": None},
        {"tool": "get_order", "reason": "business_rule_denied", "control": "regla_flujo"},
    ]


def test_attempt_and_denial_fields_match_the_closed_public_list() -> None:
    _, payload = leaking_board()

    for session_item in payload["sessions"]:
        for item in session_item["attempts"]:
            assert set(item) == ATTEMPT_KEYS
            for denial in item["denials"]:
                assert set(denial) == DENIAL_KEYS


def test_denial_control_maps_validators_to_a_closed_category() -> None:
    assert denial_control(None) is None
    assert denial_control("order_belongs_to_session_customer") == "pedido_ajeno"
    assert denial_control("order_exists") == "pedido_inexistente"
    assert denial_control("valid_call_context") == "contexto"
    assert denial_control(RULE_VALIDATOR) == "regla_flujo"
    assert denial_control("validador_nuevo") == "otro"
