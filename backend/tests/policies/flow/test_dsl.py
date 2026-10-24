import pytest
from pydantic import ValidationError

from agent_zero.policies.flow.dsl import FlowPolicy, FlowRule, covered_controls, merge
from agent_zero.policies.validator_catalog import ValidatorName


def rule(rule_id: str, tool: str, condition: dict[str, object]) -> FlowRule:
    return FlowRule.model_validate(
        {"rule_id": rule_id, "tool": tool, "deny_when": condition, "reason": "Motivo."}
    )


def test_grammar_rejects_unknown_tools_conditions_and_extra_fields() -> None:
    with pytest.raises(ValidationError):
        rule("borrar_todo", "delete_orders", {"kind": "not_session_owner"})
    with pytest.raises(ValidationError):
        rule("permitir", "get_order", {"kind": "allow_all"})
    with pytest.raises(ValidationError):
        FlowRule.model_validate(
            {
                "rule_id": "extra",
                "tool": "get_order",
                "deny_when": {"kind": "not_session_owner"},
                "reason": "Motivo.",
                "allow": True,
            }
        )


def test_amount_conditions_only_apply_to_refunds() -> None:
    with pytest.raises(ValidationError):
        rule("importe_pedido", "get_order", {"kind": "untrusted_origin", "argument": "amount"})
    assert rule("importe", "request_refund", {"kind": "exceeds", "argument": "amount", "limit": 20})


def test_policy_has_between_one_and_three_rules() -> None:
    owner = rule("ajeno", "get_order", {"kind": "not_session_owner"})
    with pytest.raises(ValidationError):
        FlowPolicy(rules=[], rationale="Nada.")
    with pytest.raises(ValidationError):
        FlowPolicy(rules=[owner] * 4, rationale="Demasiadas.")


def test_merge_deduplicates_by_effect_and_maps_to_catalog_controls() -> None:
    owner = rule("ajeno", "get_order", {"kind": "not_session_owner"})
    same = rule("otro_nombre", "get_order", {"kind": "not_session_owner"})
    limit = rule("tope", "request_refund", {"kind": "exceeds", "argument": "amount", "limit": 20})
    loose = rule(
        "tope_alto", "request_refund", {"kind": "exceeds", "argument": "amount", "limit": 99}
    )
    origin = rule("origen", "request_refund", {"kind": "untrusted_origin", "argument": "amount"})
    assert len(merge([owner], [same, limit])) == 2
    assert covered_controls([owner, limit, origin]) == {
        ValidatorName.ORDER_OWNER,
        ValidatorName.REFUND_LIMIT,
        ValidatorName.PROVENANCE,
    }
    assert covered_controls([loose]) == set()
