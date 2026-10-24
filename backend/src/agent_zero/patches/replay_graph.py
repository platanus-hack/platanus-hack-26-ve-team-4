import re
from typing import Any

from agent_zero.oracles.schemas import Assessment, ToolEvidence
from agent_zero.policies.validator_catalog import ValidatorName

MAX_CALLS = 6
TOOL_NAME = re.compile(r"^[a-z_]{1,40}$")
EFFECTS: dict[str, tuple[str, str]] = {
    "OBJ-ORDER": ("foreign_order_read", "Pedido ajeno leído"),
    "OBJ-REFUND": ("refund_over_limit", "Reembolso indebido"),
    "OBJ-MEMORY": ("permission_memory", "Permiso guardado en memoria"),
}
CONTROLS = frozenset(item.value for item in ValidatorName)
FLOW_CONTROL = re.compile(r"flow:[a-z][a-z0-9_]{2,40}")


def violation_effects(assessment: Assessment) -> dict[int, str]:
    return {
        event_id: verdict.objective_id
        for verdict in assessment.verdicts
        if verdict.violated and verdict.objective_id in EFFECTS
        for event_id in verdict.evidence_event_ids
    }


def tool_label(tool: str) -> str:
    return tool if TOOL_NAME.match(tool) else "herramienta"


def control_label(validator: str) -> str:
    if validator in CONTROLS or FLOW_CONTROL.fullmatch(validator):
        return validator
    return "control"


def build_graph(
    evidence: list[ToolEvidence],
    effects: dict[int, str],
    decisions: dict[int, str | None] | None = None,
) -> dict[str, Any]:
    nodes: list[dict[str, str]] = [{"id": "agent", "kind": "agent", "label": "Agente de soporte"}]
    edges: list[dict[str, str]] = []
    completed = [item for item in evidence if item.kind == "tool_completed"][:MAX_CALLS]
    for index, item in enumerate(completed):
        tool_id = f"tool-{index}"
        nodes.append({"id": tool_id, "kind": "tool", "label": tool_label(item.tool), "state": "ok"})
        edges.append({"from": "agent", "to": tool_id, "state": "ok"})
        objective = effects.get(item.event_id)
        if objective is None:
            continue
        effect_type, label = EFFECTS[objective]
        effect_id = f"effect-{index}"
        validator = None if decisions is None else decisions.get(item.event_id)
        nodes.append(
            {
                "id": effect_id,
                "kind": "effect",
                "label": label,
                "effect": effect_type,
                "state": "effect" if validator is None else "prevented",
            }
        )
        edge = {
            "from": tool_id,
            "to": effect_id,
            "state": "effect" if validator is None else "blocked",
        }
        if validator is not None:
            edge["control"] = control_label(validator)
        edges.append(edge)
    return {"nodes": nodes, "edges": edges}
