import pytest

from agent_zero.contract.conditions import CallFacts, Exceeds, NotOwner
from agent_zero.contract.loader import ContractError, parse_contract
from agent_zero.contract.schema import PolicyRule
from tests.contract.support import CONTRACTS_DIR, shipped

BASE = (CONTRACTS_DIR / "yummy-soporte.yaml").read_text(encoding="utf-8")


def test_violations_name_every_broken_invariant() -> None:
    contract = shipped()["yummy-soporte"]
    facts = CallFacts(
        "request_refund", {"order_id": "B-1", "amount": 90}, "ana", {}, {"order_id": "bruno"}
    )
    broken = {invariant.id for invariant in contract.violations(facts)}
    assert broken == {"solo-pedidos-propios", "reembolso-dentro-del-limite"}


def test_conditions_must_fit_the_argument_kind() -> None:
    contract = shipped()["yummy-soporte"]
    wrong = PolicyRule(
        rule_id="r_wrong",
        tool="request_refund",
        deny_when=Exceeds(kind="exceeds", argument="order_id", limit=1),
        reason="x",
    )
    with pytest.raises(ValueError, match="no aplica"):
        contract.require_rule(wrong)
    missing = wrong.model_copy(update={"deny_when": NotOwner(kind="not_owner", argument="x")})
    with pytest.raises(ValueError, match="no tiene"):
        contract.require_rule(missing)


def test_a_legitimate_example_that_breaks_an_invariant_is_rejected() -> None:
    broken = BASE.replace(
        "arguments: {order_id: A-1001, amount: 5}", "arguments: {order_id: A-1001, amount: 50}"
    )
    with pytest.raises(ContractError, match="rompe reembolso-dentro-del-limite"):
        parse_contract(broken)


def test_unknown_tools_and_bad_names_are_rejected() -> None:
    with pytest.raises(ContractError, match="desconocida"):
        parse_contract(
            BASE.replace("tools: [get_order, request_refund]", "tools: [get_order, borrar]")
        )
    with pytest.raises(ContractError, match="inválido"):
        parse_contract(BASE.replace("  search_knowledge:", "  'buscar; drop':"))
