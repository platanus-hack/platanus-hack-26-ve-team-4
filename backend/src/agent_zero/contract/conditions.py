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


class WindowExceeds(_Condition):
    kind: Literal["window_exceeds"]
    limit: float = Field(gt=0)
    window_seconds: int = Field(ge=60, le=2_592_000)

    def total_key(self) -> str:
        return f"{self.argument}@{self.window_seconds}"


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
    Exceeds | WindowExceeds | NotOwner | UntrustedOrigin | NotIn | ContainsAny,
    Field(discriminator="kind"),
]
ACCEPTED_KINDS: dict[str, frozenset[str]] = {
    "exceeds": frozenset({"amount"}),
    "window_exceeds": frozenset({"amount"}),
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
    totals: Mapping[str, float] = field(default_factory=dict)


def number_of(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _over_limit(condition: Exceeds | WindowExceeds, value: Any, facts: CallFacts) -> bool:
    number = number_of(value)
    if number is None:
        return False
    if isinstance(condition, WindowExceeds):
        number += facts.totals.get(condition.total_key(), 0.0)
    return number > condition.limit


def holds(condition: Condition, facts: CallFacts) -> bool:
    if condition.argument not in facts.arguments:
        return False
    value = facts.arguments[condition.argument]
    if isinstance(condition, Exceeds | WindowExceeds):
        return _over_limit(condition, value, facts)
    if isinstance(condition, NotOwner):
        owner = facts.owners.get(condition.argument)
        return owner is not None and owner != facts.subject
    if isinstance(condition, UntrustedOrigin):
        return facts.provenance.get(condition.argument) in LOW_INTEGRITY
    if isinstance(condition, NotIn):
        return str(value) not in condition.allowed
    text = str(value).casefold()
    return any(term.casefold() in text for term in condition.terms)
