from agent_zero.llm.demo_flow_policy import demo_flow_policy
from agent_zero.policies.flow.dsl import FlowPolicy


def payload(tool: str, provenance: dict[str, str]) -> dict[str, object]:
    return {
        "business_limits": {"refund_limit": 20.0},
        "violating_calls": [{"tool": tool, "arguments": {}, "provenance": provenance}],
    }


def test_poisoned_refund_gets_an_origin_rule_and_a_direct_order_attack_does_not() -> None:
    poisoned = FlowPolicy.model_validate(
        demo_flow_policy(payload("request_refund", {"amount": "untrusted"}))
    )
    assert [rule.deny_when.kind for rule in poisoned.rules] == [
        "untrusted_origin",
        "exceeds",
        "not_session_owner",
    ]
    direct = FlowPolicy.model_validate(demo_flow_policy(payload("get_order", {"order_id": "user"})))
    assert [rule.deny_when.kind for rule in direct.rules] == ["not_session_owner"]
    assert "modo demo" in direct.rationale
