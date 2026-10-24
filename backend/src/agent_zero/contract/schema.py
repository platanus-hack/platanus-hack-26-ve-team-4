import hashlib
import json
import re
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from agent_zero.contract.conditions import ACCEPTED_KINDS, CallFacts, Condition, holds

Slug = Field(pattern=r"^[a-z][a-z0-9_-]{1,60}$")
TOOL_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{0,63}")
ArgumentKind = Literal["amount", "resource", "enum", "text", "identifier"]


class ArgumentSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: ArgumentKind
    description: str = ""


class ToolContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    description: str = Field(min_length=1, max_length=500)
    side_effect: bool = False
    arguments: dict[str, ArgumentSpec] = Field(min_length=1, max_length=20)


class Invariant(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Slug
    description: str = Field(min_length=1, max_length=500)
    tools: list[str] = Field(min_length=1, max_length=20)
    never: Condition


class PolicyRule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    rule_id: str = Slug
    tool: str = Field(min_length=1, max_length=60)
    deny_when: Condition
    reason: str = Field(min_length=1, max_length=300)

    def key(self) -> str:
        return json.dumps(
            {"tool": self.tool, "deny_when": self.deny_when.model_dump(mode="json")},
            sort_keys=True,
        )


class LegitimateCall(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Slug
    tool: str
    arguments: dict[str, Any]
    provenance: dict[str, Literal["user", "store", "untrusted", "memory", "model"]] = {}
    owners: dict[str, str] = {}

    def facts(self, subject: str) -> CallFacts:
        owners = {name: subject if raw == "subject" else raw for name, raw in self.owners.items()}
        return CallFacts(self.tool, self.arguments, subject, self.provenance, owners)


class DomainContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_id: str = Slug
    version: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=1000)
    subject: str = Field(min_length=1, max_length=60)
    tools: dict[str, ToolContract] = Field(min_length=1, max_length=50)
    invariants: list[Invariant] = Field(min_length=1, max_length=50)
    legitimate: list[LegitimateCall] = Field(min_length=1, max_length=50)
    auto_activate: bool = True
    enforce_invariants: bool = False

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        for name in self.tools:
            if not TOOL_NAME.fullmatch(name):
                raise ValueError(f"Nombre de herramienta inválido: {name}.")
        for invariant in self.invariants:
            for tool in invariant.tools:
                self.require_condition(tool, invariant.never)
        for call in self.legitimate:
            if call.tool not in self.tools:
                raise ValueError(
                    f"La llamada legítima {call.name} usa una herramienta desconocida."
                )
            broken = self.violations(call.facts("subject"))
            if broken:
                raise ValueError(f"La llamada legítima {call.name} rompe {broken[0].id}.")
        return self

    def require_condition(self, tool: str, condition: Condition) -> None:
        spec = self.tools.get(tool)
        if spec is None:
            raise ValueError(f"Herramienta desconocida: {tool}.")
        argument = spec.arguments.get(condition.argument)
        if argument is None:
            raise ValueError(f"{tool} no tiene el argumento {condition.argument}.")
        if argument.kind not in ACCEPTED_KINDS[condition.kind]:
            raise ValueError(f"{condition.kind} no aplica a un argumento {argument.kind}.")

    def require_rule(self, rule: PolicyRule) -> PolicyRule:
        self.require_condition(rule.tool, rule.deny_when)
        return rule

    def violations(self, facts: CallFacts) -> list[Invariant]:
        return [
            invariant
            for invariant in self.invariants
            if facts.tool in invariant.tools and holds(invariant.never, facts)
        ]

    def digest(self) -> str:
        raw = json.dumps(self.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode()).hexdigest()
