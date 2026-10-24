from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from agent_zero.agent_gateway.business_policy import BusinessDenial
from agent_zero.policies.flow.dsl import (
    LOW_INTEGRITY,
    Exceeds,
    FlowCondition,
    FlowRule,
    NotSessionOwner,
    UntrustedOrigin,
)


@dataclass(frozen=True)
class CallFacts:
    parsed: Mapping[str, Any]
    provenance: Mapping[str, str]
    owner: str | None
    customer: str


def holds(condition: FlowCondition, facts: CallFacts) -> bool:
    if isinstance(condition, UntrustedOrigin):
        return facts.provenance.get(condition.argument) in LOW_INTEGRITY
    if isinstance(condition, Exceeds):
        return float(facts.parsed[condition.argument]) > condition.limit
    if isinstance(condition, NotSessionOwner):
        return facts.owner is not None and facts.owner != facts.customer
    return False


def evaluate(rules: list[FlowRule], tool: str, facts: CallFacts) -> BusinessDenial | None:
    for rule in rules:
        if rule.tool == tool and holds(rule.deny_when, facts):
            return BusinessDenial(f"flow:{rule.rule_id}", rule.reason)
    return None
