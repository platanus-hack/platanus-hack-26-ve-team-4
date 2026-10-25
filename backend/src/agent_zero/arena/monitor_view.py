from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from agent_zero.attempts.models import Attempt, AttemptStatus
from agent_zero.llm.schemas import CallCost, CallRecord, CallUsage
from agent_zero.oracles.schemas import Assessment, ToolEvidence
from agent_zero.patches.replay_graph import (
    EFFECTS,
    MAX_CALLS,
    control_label,
    tool_label,
    violation_effects,
)

DENIED = ("tool_denied", "Llamada denegada")
TERMINAL = {AttemptStatus.EVALUATED, AttemptStatus.INCONCLUSIVE}


def usage_view(records: Iterable[CallRecord]) -> dict[str, Any]:
    items = list(records)
    usage = sum((record.usage for record in items if record.usage), CallUsage())
    cost = sum((record.cost for record in items if record.cost), CallCost())
    return {
        "calls": len(items),
        "measured_calls": sum(record.measured for record in items),
        "input_tokens": usage.prompt_tokens,
        "output_tokens": usage.output_tokens,
        "cost_usd": round(cost.total_usd, 7),
    }


def usage_by_attempt(records: Iterable[CallRecord]) -> dict[str, list[CallRecord]]:
    grouped: defaultdict[str, list[CallRecord]] = defaultdict(list)
    for record in records:
        if record.scope.attempt_id:
            grouped[record.scope.attempt_id].append(record)
    return grouped


def attempt_patch(finding_id: str | None, policies: list[dict[str, Any]]) -> dict[str, Any] | None:
    if finding_id is None:
        return None
    for policy in policies:
        if finding_id in policy["finding_ids"] and policy["validation"].get("passed") is True:
            return {
                "version": policy["version"],
                "status": policy["status"],
                "activated_at": policy["activated_at"],
                "replay": isinstance(policy["validation"].get("replay"), dict),
            }
    return None


def attempt_row(
    attempt: Attempt,
    records: list[CallRecord],
    finding: dict[str, Any] | None,
    campaign_family: str | None,
    policies: list[dict[str, Any]],
) -> dict[str, Any]:
    analysis = (finding or {}).get("analysis") or {}
    family, source = campaign_family, "campaign"
    if family is None and isinstance(analysis.get("attack_family"), str):
        family, source = analysis["attack_family"], "analyzer"
    finding_id = None if finding is None else finding["id"]
    return {
        "id": attempt.id,
        "created_at": attempt.created_at.isoformat(),
        "updated_at": attempt.updated_at.isoformat(),
        "origin": attempt.origin,
        "status": attempt.status.value,
        "outcome": attempt.outcome.value if attempt.outcome else None,
        "route": attempt.route.value,
        "policy_version": attempt.policy_version,
        "messages": attempt.messages,
        "family": family,
        "family_source": source if family else None,
        "signals": (attempt.assessment or {}).get("signals", []),
        "finding_id": finding_id,
        "patch": attempt_patch(finding_id, policies),
        "duration_seconds": (attempt.updated_at - attempt.created_at).total_seconds()
        if attempt.status in TERMINAL
        else None,
        "usage": usage_view(records),
    }


def attempt_graph(evidence: list[ToolEvidence], assessment: dict[str, Any]) -> dict[str, Any]:
    """Grafo de las llamadas del propio intento: efecto indebido o denegación del gateway."""
    effects = violation_effects(Assessment.model_validate(assessment)) if assessment else {}
    nodes: list[dict[str, str]] = [{"id": "agent", "kind": "agent", "label": "Agente de soporte"}]
    edges: list[dict[str, str]] = []
    calls = [item for item in evidence if item.kind in {"tool_completed", "tool_denied"}]
    for index, item in enumerate(calls[:MAX_CALLS]):
        tool_id, effect_id = f"tool-{index}", f"effect-{index}"
        nodes.append({"id": tool_id, "kind": "tool", "label": tool_label(item.tool), "state": "ok"})
        edges.append({"from": "agent", "to": tool_id, "state": "ok"})
        if item.kind == "tool_denied":
            effect_type, label = DENIED
            nodes.append(
                {
                    "id": effect_id,
                    "kind": "effect",
                    "label": label,
                    "effect": effect_type,
                    "state": "prevented",
                }
            )
            edges.append(
                {
                    "from": tool_id,
                    "to": effect_id,
                    "state": "blocked",
                    "control": control_label(item.validator),
                }
            )
            continue
        objective = effects.get(item.event_id)
        if objective is None:
            continue
        effect_type, label = EFFECTS[objective]
        nodes.append(
            {
                "id": effect_id,
                "kind": "effect",
                "label": label,
                "effect": effect_type,
                "state": "effect",
            }
        )
        edges.append({"from": tool_id, "to": effect_id, "state": "effect"})
    return {"nodes": nodes, "edges": edges}
