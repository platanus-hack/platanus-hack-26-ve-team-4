from collections.abc import Iterable

from agent_zero.contract.conditions import CallFacts, holds
from agent_zero.contract.schema import DomainContract, PolicyRule

PROBE_SUBJECT = "sujeto-legitimo"


def first_denial(rules: Iterable[PolicyRule], facts: CallFacts) -> PolicyRule | None:
    return next(
        (rule for rule in rules if rule.tool == facts.tool and holds(rule.deny_when, facts)),
        None,
    )


def legitimate_facts(contract: DomainContract) -> list[CallFacts]:
    return [call.facts(PROBE_SUBJECT) for call in contract.legitimate]


def injected_probes(contract: DomainContract, tools: set[str]) -> list[CallFacts]:
    probes = []
    for call in contract.legitimate:
        if call.tool not in tools or not contract.tools[call.tool].side_effect:
            continue
        base = call.facts(PROBE_SUBJECT)
        tainted = dict.fromkeys(base.arguments, "untrusted")
        probes.append(CallFacts(base.tool, base.arguments, base.subject, tainted, base.owners))
    return probes


def gate(
    contract: DomainContract, rules: list[PolicyRule], violating: list[CallFacts]
) -> dict[str, int | bool]:
    blocked = sum(1 for facts in violating if first_denial(rules, facts))
    legitimate = legitimate_facts(contract)
    kept = sum(1 for facts in legitimate if first_denial(rules, facts) is None)
    probes = injected_probes(contract, {facts.tool for facts in violating})
    return {
        "accepted": blocked == len(violating) and kept == len(legitimate),
        "original_blocked": blocked,
        "original_total": len(violating),
        "legitimate_kept": kept,
        "legitimate_total": len(legitimate),
        "injected_blocked": sum(1 for facts in probes if first_denial(rules, facts)),
        "injected_total": len(probes),
    }
