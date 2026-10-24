from typing import Any

from agent_zero.contract.conditions import Condition
from agent_zero.contract.schema import PolicyRule
from agent_zero.guard.models import GuardFindingRecord, GuardPolicyRecord


def clause(condition: Condition) -> str:
    data = condition.model_dump(mode="json")
    if data["kind"] == "exceeds":
        return f"{condition.argument} > {data['limit']:g}"
    if data["kind"] == "not_owner":
        return f"{condition.argument} no pertenece al sujeto"
    if data["kind"] == "untrusted_origin":
        return f"{condition.argument} viene de una fuente no confiable"
    if data["kind"] == "not_in":
        return f"{condition.argument} fuera de {data['allowed']}"
    return f"{condition.argument} contiene {data['terms']}"


def render(rule: PolicyRule) -> str:
    return f"DENEGAR {rule.tool} SI {clause(rule.deny_when)}"


def policy_view(record: GuardPolicyRecord) -> dict[str, Any]:
    rules = [PolicyRule.model_validate(raw) for raw in record.rules]
    return {
        "version": record.version,
        "parent_version": record.parent_version,
        "status": record.status,
        "rules": [{**rule.model_dump(mode="json"), "text": render(rule)} for rule in rules],
        "report": record.report,
        "finding_id": record.finding_id,
        "contract_digest": record.contract_digest,
        "created_at": record.created_at.isoformat(),
    }


def finding_view(record: GuardFindingRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "call_id": record.call_id,
        "invariant_ids": record.invariant_ids,
        "policy_version": record.policy_version,
        "resolved_by": record.resolved_by,
        "created_at": record.created_at.isoformat(),
    }
