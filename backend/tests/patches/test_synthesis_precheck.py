from agent_zero.oracles.schemas import ToolEvidence
from agent_zero.patches.synthesis_precheck import precheck, recorded_owner
from agent_zero.policies.flow.dsl import FlowPolicy
from agent_zero.victim.fixtures import orders_for_customer

REFUND = ToolEvidence(
    event_id=3,
    kind="tool_completed",
    tool="request_refund",
    arguments={"order_id": "A-1001", "amount": 25.0},
    output={"customer_id": "cust-ana"},
    provenance={"order_id": "untrusted", "amount": "untrusted"},
)


def policy(*conditions: dict[str, object]) -> FlowPolicy:
    return FlowPolicy.model_validate(
        {
            "rules": [
                {
                    "rule_id": f"regla_{index}",
                    "tool": "request_refund",
                    "deny_when": item,
                    "reason": "R.",
                }
                for index, item in enumerate(conditions)
            ],
            "rationale": "Prueba.",
        }
    )


def test_accepts_a_rule_that_blocks_the_trace_and_keeps_legitimate_calls() -> None:
    gate = precheck(
        policy({"kind": "untrusted_origin", "argument": "amount"}), [REFUND], "cust-ana"
    )
    assert gate["accepted"] is True
    assert (gate["original_blocked"], gate["legitimate_kept"]) == (1, 3)


def test_rejects_trivial_and_excessive_rules() -> None:
    trivial = precheck(policy({"kind": "not_session_owner"}), [REFUND], "cust-ana")
    assert trivial["accepted"] is False
    assert "no bloquea" in trivial["reason"]
    excessive = precheck(
        policy({"kind": "exceeds", "argument": "amount", "limit": 1}), [REFUND], "cust-ana"
    )
    assert excessive["accepted"] is False
    assert "valid-refund" in excessive["reason"]
    assert precheck(policy({"kind": "not_session_owner"}), [], "cust-ana")["accepted"] is False


def test_owner_falls_back_to_the_fixture_orders() -> None:
    assert recorded_owner(REFUND.model_copy(update={"output": {}})) == "cust-ana"


def test_owner_comes_from_the_structured_effect_for_demo_customers() -> None:
    order_id = orders_for_customer("cust-demo-0044")[0].order_id
    item = ToolEvidence(
        event_id=4,
        kind="tool_completed",
        tool="request_refund",
        arguments={"order_id": order_id, "amount": 5.0},
        output={"approved": True, "order_id": order_id},
        effect={"kind": "refund", "order_id": order_id, "owner_customer_id": "cust-demo-0044"},
        provenance={"order_id": "untrusted"},
    )
    assert recorded_owner(item) == "cust-demo-0044"
    legacy = item.model_copy(update={"effect": {}, "output": {"customer_id": "cust-demo-0044"}})
    assert recorded_owner(legacy) == "cust-demo-0044"
