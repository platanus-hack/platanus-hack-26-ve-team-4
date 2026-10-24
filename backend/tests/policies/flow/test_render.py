from agent_zero.policies.flow.dsl import FlowRule
from agent_zero.policies.flow.render import render


def test_rules_render_as_one_readable_line() -> None:
    rule = FlowRule.model_validate(
        {
            "rule_id": "tope",
            "tool": "request_refund",
            "deny_when": {"kind": "exceeds", "argument": "amount", "limit": 20},
            "reason": "Tope.",
        }
    )
    assert render(rule) == "DENEGAR request_refund SI amount > 20"
