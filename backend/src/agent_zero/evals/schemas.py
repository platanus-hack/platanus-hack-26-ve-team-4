from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from agent_zero.prober.models import AttackFamily, Surface
from agent_zero.victim.controlled_fixtures import ControlledFixture


class ToolExpectation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tool: Literal["get_order", "request_refund", "search_knowledge", "save_memory"]
    arguments: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)


class EvaluationCase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    customer_id: str
    adversarial: bool
    family: AttackFamily | None = None
    surface: Surface = Surface.MESSAGE
    partition: Literal["discovery", "reserved", "legitimate"]
    objective_id: str | None = None
    messages: list[str] = Field(min_length=1, max_length=4)
    fixture: ControlledFixture | None = None
    critical: bool = False
    expected_tools: list[ToolExpectation] = Field(default_factory=list)
    reply_contains: list[str] = Field(default_factory=list)


class EvaluationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    before_version: int = Field(default=0, ge=0)
    after_version: int = Field(ge=0)
    repetitions: int = Field(default=3, ge=1, le=3)
    max_calls: int = Field(default=1200, ge=1, le=5000)
