from agent_zero.policies.flow.dsl import FlowPolicy, FlowRule
from agent_zero.policies.flow.proposal import FlowProposal, compose

OWNER = FlowRule.model_validate(
    {
        "rule_id": "ajeno",
        "tool": "get_order",
        "deny_when": {"kind": "not_session_owner"},
        "reason": "Pedido ajeno.",
    }
)


def test_synthesized_policy_keeps_the_catalog_and_adds_flow_rules() -> None:
    proposal = FlowProposal(FlowPolicy(rules=[OWNER], rationale="Motivo."), {"status": "accepted"})
    composed = compose([], [], [("f1", "OBJ-ORDER")], proposal)
    assert composed is not None
    assert composed.rules == []
    assert [rule["rule_id"] for rule in composed.flow_rules] == ["ajeno"]
    assert composed.synthesis["source"] == "synthesized"
    assert compose([], [OWNER], [("f1", "OBJ-ORDER")], proposal) is None


def test_catalog_fallback_inherits_parent_flow_rules() -> None:
    rejected = FlowProposal(None, {"status": "rejected"})
    composed = compose([], [OWNER], [("f1", "OBJ-REFUND")], rejected)
    assert composed is not None
    assert composed.rules == ["order_belongs_to_session_customer", "refund_within_limit"]
    assert [rule["rule_id"] for rule in composed.flow_rules] == ["ajeno"]
    assert composed.synthesis == {"source": "inherited"}
