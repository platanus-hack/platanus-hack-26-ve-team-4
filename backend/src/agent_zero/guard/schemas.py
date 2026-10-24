from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Origin = Literal["user", "store", "untrusted", "memory"]


class ContextSegment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    origin: Origin
    text: str = Field(max_length=20000)


class CheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: str = Field(min_length=1, max_length=128)
    tool: str = Field(min_length=1, max_length=64)
    arguments: dict[str, Any] = Field(max_length=20)
    context: list[ContextSegment] = Field(default=[], max_length=200)
    provenance: dict[str, Origin | Literal["model"]] = {}
    owners: dict[str, str] = {}


class Decision(BaseModel):
    call_id: str
    allowed: bool
    rule_id: str | None = None
    reason: str | None = None
    policy_version: int
    provenance: dict[str, str]
    learned: dict[str, Any] | None = None


class EffectReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    call_id: str = Field(min_length=1, max_length=40)
    arguments: dict[str, Any] | None = None
    owners: dict[str, str] = {}


class EffectVerdict(BaseModel):
    call_id: str
    violations: list[str]
    finding_id: str | None = None
    policy: dict[str, Any] | None = None
