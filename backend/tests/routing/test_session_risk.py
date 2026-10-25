import pytest

from agent_zero.routing.session_risk import ToolOutcome, is_near_miss, risk_score

pytestmark = pytest.mark.requirement("CORE-06")

OWN = ["D-21001", "D-21002"]


def denied(validator: str, order_id: str | None = None, tool: str = "get_order") -> ToolOutcome:
    return ToolOutcome(tool=tool, denied=True, validator=validator, order_id=order_id)


def completed(order_id: str, tool: str = "get_order") -> ToolOutcome:
    return ToolOutcome(tool=tool, denied=False, validator=None, order_id=order_id)


def test_typos_near_own_orders_cost_nothing() -> None:
    typos = [denied("order_exists", order) for order in ["D-2101", "D-21010", "d-21092 "]]
    assert risk_score(typos, OWN) == 0


def test_an_honest_customer_with_far_typos_stays_under_threshold() -> None:
    outcomes = [denied("order_exists", "D-0002"), completed("D-21001")]
    outcomes += [denied("order_exists", "D-9"), denied("order_exists", "X-4444")]
    assert risk_score(outcomes, OWN) < 6


def test_two_foreign_orders_reach_the_threshold() -> None:
    outcomes = [denied("order_belongs_to_session_customer", "B-2001")]
    outcomes += [completed("D-21001"), denied("order_belongs_to_session_customer", "A-1001")]
    assert risk_score(outcomes, OWN) >= 6


def test_interleaved_successes_do_not_reset_enumeration() -> None:
    outcomes: list[ToolOutcome] = []
    for order in ["A-1001", "B-2001", "C-3001", "Z-7777"]:
        outcomes += [denied("order_exists", order), completed("D-21001")]
    assert risk_score(outcomes, OWN) == 6


def test_own_orders_never_count_as_enumeration() -> None:
    outcomes = [completed(order) for order in OWN * 3]
    assert risk_score(outcomes, OWN) == 0


def test_refund_memory_and_flow_denials_weigh_two() -> None:
    outcomes = [
        denied("refund_within_limit", "D-21001", "request_refund"),
        denied("memory_key_allowlist", tool="save_memory"),
        denied("flow:rule-1", "D-21001"),
    ]
    assert risk_score(outcomes, OWN) == 6


def test_unknown_validators_cost_nothing() -> None:
    assert risk_score([denied("something_new", "D-21001")], OWN) == 0


def test_near_miss_ignores_case_and_spaces() -> None:
    assert is_near_miss(" d-21002", OWN)
    assert not is_near_miss("B-2001", OWN)
    assert not is_near_miss("D-0002", OWN)
