from typing import Any

from agent_zero.attempts.models import Attempt
from agent_zero.oracles.schemas import Assessment, ToolEvidence
from agent_zero.patches.replay_graph import build_graph, violation_effects
from agent_zero.patches.validation_cases import validation_cases
from agent_zero.routing.models import Route

SOURCE = "repetición de las llamadas a herramientas registradas"


def legit_rows(
    objective: str, original: Attempt, results: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    tools = {
        case.name: case.required_tool
        for case in validation_cases(objective, original.customer_id, original.messages)
        if not case.adversarial
    }
    return [
        {"name": result["name"], "passed": result["passed"] is True, "tool": tools[result["name"]]}
        for result in results
        if result["name"] in tools
    ]


def build_replay(
    version: int,
    original: Attempt,
    evidence: list[ToolEvidence],
    decisions: dict[int, str | None],
    legit: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if original.route is not Route.PROTECTED:
        return None
    effects = violation_effects(Assessment.model_validate(original.assessment))
    if not effects:
        return None
    return {
        "source": SOURCE,
        "before": {"version": original.policy_version, "graph": build_graph(evidence, effects)},
        "after": {"version": version, "graph": build_graph(evidence, effects, decisions)},
        "legit": legit,
    }
