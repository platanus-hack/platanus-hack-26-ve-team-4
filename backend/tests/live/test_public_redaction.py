import json
from typing import Any

from agent_zero.attempts.models import Attempt, AttemptOutcome
from agent_zero.live.models import LiveBoard, LiveDenial
from agent_zero.live.redaction import redact_live
from agent_zero.live.service import BoardData, build_board
from agent_zero.routing.models import Route
from agent_zero.sessions.models import ArenaSession
from tests.live.support import attempt, session

CANARY_HONEYPOT = "AZH_0123456789abcdef_A-1001"
CANARY_PROTECTED = "AZP_0123456789abcdef_B-2002"
HONEYTOKEN = "AZH-KEY-ABCD-EFGH-JKLM"

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
DENIAL_KEYS = {"tool", "reason", "validator"}


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
    denials = {"p1": [LiveDenial(tool="get_order", reason="rate_limited", validator=None)]}
    data = BoardData([row], sessions, [], [], [], denials, {})
    board = build_board(data, revealed=False, llm_mode="demo", limit=6, accepting=True)
    return board, json.loads(board.model_dump_json())


def test_redact_live_removes_canaries_and_honeytokens() -> None:
    text = f"A {CANARY_HONEYPOT} B {CANARY_PROTECTED} C {HONEYTOKEN} D"

    assert redact_live(text) == "A [referencia] B [referencia] C [referencia] D"


def test_the_public_board_never_leaks_internal_references_before_the_reveal() -> None:
    board, payload = leaking_board()
    dumped = board.model_dump_json()

    for leaked in (CANARY_PROTECTED, "AZP_", "AZH_", "AZH-KEY", "rule_id", "arguments"):
        assert leaked not in dumped
    for word in ("args", "trace"):
        assert word not in dumped

    item = payload["sessions"][0]["attempts"][0]
    assert item["outcome"] == "contained_honeypot"
    assert item["route"] == "honeypot"
    assert "[referencia]" in item["reply"]
    assert item["messages"] == ["Mi clave es [referencia]."]
    assert item["denials"] == [{"tool": "get_order", "reason": "rate_limited", "validator": None}]


def test_attempt_and_denial_fields_match_the_closed_public_list() -> None:
    _, payload = leaking_board()

    for session_item in payload["sessions"]:
        for item in session_item["attempts"]:
            assert set(item) == ATTEMPT_KEYS
            for denial in item["denials"]:
                assert set(denial) == DENIAL_KEYS
