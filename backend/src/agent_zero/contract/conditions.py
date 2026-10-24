from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

LOW_INTEGRITY = frozenset({"untrusted", "memory"})
ORIGINS = ("user", "store", "untrusted", "memory", "model")


class _Condition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    argument: str = Field(min_length=1, max_length=60)


class Exceeds(_Condition):
    kind: Literal["exceeds"]
    limit: float


class NotOwner(_Condition):
    kind: Literal["not_owner"]


class UntrustedOrigin(_Condition):
    kind: Literal["untrusted_origin"]


class NotIn(_Condition):
    kind: Literal["not_in"]
    allowed: list[str] = Field(min_length=1, max_length=50)


class ContainsAny(_Condition):
    kind: Literal["contains_any"]
    terms: list[str] = Field(min_length=1, max_length=50)


Condition = Annotated[
    Exceeds | NotOwner | UntrustedOrigin | NotIn | ContainsAny, Field(discriminator="kind")
]
ACCEPTED_KINDS: dict[str, frozenset[str]] = {
    "exceeds": frozenset({"amount"}),
    "not_owner": frozenset({"resource"}),
    "untrusted_origin": frozenset({"amount", "resource", "enum", "text", "identifier"}),
    "not_in": frozenset({"enum", "identifier", "text"}),
    "contains_any": frozenset({"text", "enum", "identifier"}),
}


@dataclass(frozen=True)
class CallFacts:
    tool: str
    arguments: Mapping[str, Any]
    subject: str
    provenance: Mapping[str, str] = field(default_factory=dict)
    owners: Mapping[str, str | None] = field(default_factory=dict)


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def holds(condition: Condition, facts: CallFacts) -> bool:
    if condition.argument not in facts.arguments:
        return False
    value = facts.arguments[condition.argument]
    if isinstance(condition, Exceeds):
        number = _number(value)
        return number is not None and number > condition.limit
    if isinstance(condition, NotOwner):
        owner = facts.owners.get(condition.argument)
        return owner is not None and owner != facts.subject
    if isinstance(condition, UntrustedOrigin):
        return facts.provenance.get(condition.argument) in LOW_INTEGRITY
    if isinstance(condition, NotIn):
        return str(value) not in condition.allowed
    text = str(value).casefold()
    return any(term.casefold() in text for term in condition.terms)
