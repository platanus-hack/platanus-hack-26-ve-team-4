from typing import Any

from agent_zero.attempts.models import AttemptOutcome
from agent_zero.oracles.schemas import Assessment
from agent_zero.patches.replay_report import SOURCE, build_replay, legit_rows
from agent_zero.routing.models import Route
from tests.arena.replay_support import attempt, evidence, violated

OWNER = "order_belongs_to_session_customer"


def results() -> list[dict[str, Any]]:
    return [
        {"name": "original", "adversarial": True, "passed": True},
        {"name": "own-order", "adversarial": False, "passed": True},
        {"name": "valid-refund", "adversarial": False, "passed": True},
    ]


def test_report_pairs_versions_and_legitimate_rows() -> None:
    original = attempt(Route.PROTECTED, violated(3))
    report = build_replay(
        2,
        original,
        [evidence(3, "get_order")],
        {3: OWNER},
        legit_rows("OBJ-ORDER", original, results()),
    )
    assert report is not None
    assert report["source"] == SOURCE
    assert report["before"]["version"] == 0
    assert report["after"]["version"] == 2
    assert report["before"]["graph"]["edges"][-1]["state"] == "effect"
    assert report["after"]["graph"]["edges"][-1]["state"] == "blocked"
    assert report["legit"] == [
        {"name": "own-order", "passed": True, "tool": "get_order"},
        {"name": "valid-refund", "passed": True, "tool": "request_refund"},
    ]


def test_report_is_deterministic() -> None:
    original = attempt(Route.PROTECTED, violated(3))
    calls = [evidence(3, "get_order")]
    first = build_replay(
        2, original, calls, {3: OWNER}, legit_rows("OBJ-ORDER", original, results())
    )
    second = build_replay(
        2, original, calls, {3: OWNER}, legit_rows("OBJ-ORDER", original, results())
    )
    assert first == second


def test_report_requires_a_violation() -> None:
    clean = Assessment(outcome=AttemptOutcome.NOT_ACHIEVED, verdicts=[])
    assert build_replay(2, attempt(Route.PROTECTED, clean), [], {}, []) is None


def test_honeypot_attempts_never_produce_a_replay() -> None:
    original = attempt(Route.HONEYPOT, violated(3))
    report = build_replay(2, original, [evidence(3, "get_order")], {3: OWNER}, [])
    assert report is None
