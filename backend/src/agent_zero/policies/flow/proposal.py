from dataclasses import dataclass, field
from typing import Any

from agent_zero.policies.flow.dsl import FlowPolicy, FlowRule, merge
from agent_zero.policies.validator_catalog import CONTROL_REASONS, OBJECTIVE_CONTROLS


@dataclass(frozen=True)
class FlowProposal:
    policy: FlowPolicy | None
    synthesis: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Composition:
    rules: list[str]
    flow_rules: list[dict[str, Any]]
    reason: str
    synthesis: dict[str, Any]


def compose(
    active_rules: list[str],
    parent_flow: list[FlowRule],
    targets: list[tuple[str, str]],
    flow: FlowProposal | None,
) -> Composition | None:
    inherited = [rule.model_dump(mode="json") for rule in parent_flow]
    if flow is not None and flow.policy is not None:
        merged = merge(parent_flow, flow.policy.rules)
        if [rule.key() for rule in merged] == [rule.key() for rule in parent_flow]:
            return None
        return Composition(
            rules=list(active_rules),
            flow_rules=[rule.model_dump(mode="json") for rule in merged],
            reason=flow.policy.rationale,
            synthesis=flow.synthesis | {"source": "synthesized"},
        )
    controls = {control for _, objective in targets for control in OBJECTIVE_CONTROLS[objective]}
    rules = sorted(set(active_rules) | controls)
    if rules == active_rules:
        return None
    return Composition(
        rules=rules,
        flow_rules=inherited,
        reason=" ".join(dict.fromkeys(CONTROL_REASONS[objective] for _, objective in targets)),
        synthesis={"source": "inherited"} if inherited else {},
    )
