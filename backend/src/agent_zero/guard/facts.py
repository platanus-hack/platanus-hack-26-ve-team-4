from typing import Any

from agent_zero.contract.conditions import CallFacts


def dump(facts: CallFacts) -> dict[str, Any]:
    return {
        "tool": facts.tool,
        "arguments": dict(facts.arguments),
        "subject": facts.subject,
        "provenance": dict(facts.provenance),
        "owners": dict(facts.owners),
    }


def load(raw: dict[str, Any]) -> CallFacts:
    return CallFacts(
        raw["tool"], raw["arguments"], raw["subject"], raw["provenance"], raw["owners"]
    )
