from typing import Any

from agent_zero.contract.conditions import (
    ContainsAny,
    Exceeds,
    NotIn,
    NotOwner,
    UntrustedOrigin,
    WindowExceeds,
)
from agent_zero.contract.schema import DomainContract, Invariant, LegitimateCall

OUTSIDER = "sujeto-ajeno"


def violating_variant(
    contract: DomainContract, invariant: Invariant
) -> tuple[LegitimateCall, dict[str, Any], dict[str, str], dict[str, str]] | None:
    base = next((call for call in contract.legitimate if call.tool in invariant.tools), None)
    if base is None:
        return None
    arguments = dict(base.arguments)
    provenance: dict[str, str] = dict(base.provenance)
    owners = dict(base.owners)
    condition = invariant.never
    name = condition.argument
    if isinstance(condition, Exceeds | WindowExceeds):
        arguments[name] = condition.limit + 1
    elif isinstance(condition, NotOwner):
        owners[name] = OUTSIDER
    elif isinstance(condition, UntrustedOrigin):
        provenance[name] = "untrusted"
    elif isinstance(condition, NotIn):
        arguments[name] = "fuera-de-lista"
    elif isinstance(condition, ContainsAny):
        arguments[name] = f"{arguments.get(name, '')} {condition.terms[0]}".strip()
    return base, arguments, provenance, owners
