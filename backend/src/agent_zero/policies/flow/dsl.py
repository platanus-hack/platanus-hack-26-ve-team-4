import json
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from agent_zero.policies.validator_catalog import ValidatorName
from agent_zero.victim.fixtures import REFUND_LIMIT

FlowTool = Literal["get_order", "request_refund"]
LOW_INTEGRITY = frozenset({"untrusted", "memory"})


class UntrustedOrigin(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["untrusted_origin"]
    argument: Literal["order_id", "amount"]


class Exceeds(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["exceeds"]
    argument: Literal["amount"]
    limit: float = Field(ge=0, le=1000)


class NotSessionOwner(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["not_session_owner"]


FlowCondition = Annotated[UntrustedOrigin | Exceeds | NotSessionOwner, Field(discriminator="kind")]


class FlowRule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    rule_id: str = Field(pattern=r"^[a-z][a-z0-9_]{2,40}$")
    tool: FlowTool
    deny_when: FlowCondition
    reason: str = Field(min_length=1, max_length=300)

    @model_validator(mode="after")
    def _argument_belongs_to_tool(self) -> "FlowRule":
        argument = getattr(self.deny_when, "argument", None)
        if argument == "amount" and self.tool != "request_refund":
            raise ValueError("Solo request_refund recibe un importe.")
        return self

    def key(self) -> str:
        return json.dumps(
            {"tool": self.tool, "deny_when": self.deny_when.model_dump(mode="json")},
            sort_keys=True,
        )


class FlowPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    rules: list[FlowRule] = Field(min_length=1, max_length=3)
    rationale: str = Field(min_length=1, max_length=800)


def merge(parent: list[FlowRule], added: list[FlowRule]) -> list[FlowRule]:
    merged: dict[str, FlowRule] = {}
    for rule in [*parent, *added]:
        merged.setdefault(rule.key(), rule)
    return sorted(merged.values(), key=FlowRule.key)


def covered_controls(rules: list[FlowRule]) -> set[str]:
    covered: set[str] = set()
    for rule in rules:
        condition = rule.deny_when
        if isinstance(condition, NotSessionOwner):
            covered.add(ValidatorName.ORDER_OWNER)
        elif isinstance(condition, Exceeds):
            if condition.limit <= REFUND_LIMIT:
                covered.add(ValidatorName.REFUND_LIMIT)
        else:
            covered.add(ValidatorName.PROVENANCE)
    return covered
