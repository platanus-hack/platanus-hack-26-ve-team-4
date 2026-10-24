from agent_zero.policies.flow.dsl import FlowRule
from agent_zero.policies.flow.evaluator import CallFacts, evaluate

RULES = [
    FlowRule.model_validate(item)
    for item in (
        {
            "rule_id": "importe_no_confiable",
            "tool": "request_refund",
            "deny_when": {"kind": "untrusted_origin", "argument": "amount"},
            "reason": "Importe no confiable.",
        },
        {
            "rule_id": "pedido_ajeno",
            "tool": "get_order",
            "deny_when": {"kind": "not_session_owner"},
            "reason": "Pedido ajeno.",
        },
    )
]


def facts(provenance: dict[str, str], owner: str | None = "cust-ana") -> CallFacts:
    return CallFacts({"order_id": "A-1001", "amount": 10.0}, provenance, owner, "cust-ana")


def test_amount_from_a_document_is_denied_but_the_same_amount_from_the_user_is_not() -> None:
    denial = evaluate(RULES, "request_refund", facts({"amount": "untrusted"}))
    assert denial is not None
    assert denial.validator == "flow:importe_no_confiable"
    assert evaluate(RULES, "request_refund", facts({"amount": "memory"})) is not None
    assert evaluate(RULES, "request_refund", facts({"amount": "user"})) is None
    assert evaluate(RULES, "request_refund", facts({"amount": "store"})) is None


def test_ownership_rule_only_applies_to_its_tool() -> None:
    assert evaluate(RULES, "get_order", facts({}, owner="cust-bruno")) is not None
    assert evaluate(RULES, "get_order", facts({})) is None
    assert evaluate(RULES, "get_order", facts({}, owner=None)) is None
    assert evaluate(RULES, "search_knowledge", facts({"amount": "untrusted"})) is None
