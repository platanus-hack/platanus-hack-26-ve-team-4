import re

from agent_zero.contract.conditions import ACCEPTED_KINDS, LOW_INTEGRITY, CallFacts, UntrustedOrigin
from agent_zero.contract.schema import DomainContract, Invariant, PolicyRule


def _rule_id(*parts: str) -> str:
    raw = re.sub(r"[^a-z0-9_]+", "_", "_".join(parts).casefold()).strip("_")
    return f"r_{raw}"[:60]


def merge(*groups: list[PolicyRule]) -> list[PolicyRule]:
    seen: dict[str, PolicyRule] = {}
    for group in groups:
        for rule in group:
            seen.setdefault(rule.key(), rule)
    return list(seen.values())


def derived_rules(
    contract: DomainContract, violated: list[Invariant], facts: CallFacts
) -> list[PolicyRule]:
    rules = [
        PolicyRule(
            rule_id=_rule_id(tool_name, invariant.id),
            tool=tool_name,
            deny_when=invariant.never,
            reason=invariant.description,
        )
        for invariant in violated
        for tool_name in sorted({facts.tool, *invariant.tools})
    ]
    tool = contract.tools[facts.tool]
    if not tool.side_effect:
        return merge(rules)
    for name, origin in sorted(facts.provenance.items()):
        spec = tool.arguments.get(name)
        if origin not in LOW_INTEGRITY or spec is None:
            continue
        if spec.kind not in ACCEPTED_KINDS["untrusted_origin"]:
            continue
        rules.append(
            PolicyRule(
                rule_id=_rule_id(facts.tool, name, "untrusted"),
                tool=facts.tool,
                deny_when=UntrustedOrigin(kind="untrusted_origin", argument=name),
                reason=f"{name} no lo pidió el sujeto: vino de una fuente no confiable.",
            )
        )
    return merge(rules)
