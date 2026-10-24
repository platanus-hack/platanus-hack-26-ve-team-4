from pydantic import BaseModel, ConfigDict, Field

from agent_zero.agent_gateway.models import GatewayDecision, GatewayReason
from agent_zero.identity.schemas import SCOPE_PATTERN
from agent_zero.shared.classification import DataClassification


class ToolSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9_]*$")
    classification: DataClassification
    region: str = Field(min_length=1, max_length=20)
    required_scope: str = Field(pattern=SCOPE_PATTERN.pattern)


class GatewayResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    decision: GatewayDecision
    reason: GatewayReason
    output: str
