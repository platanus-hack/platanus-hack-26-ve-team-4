from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from agent_zero.attempts.models import AttemptOutcome

ObjectiveId = Literal["OBJ-ORDER", "OBJ-REFUND", "OBJ-MEMORY"]


class OracleVerdict(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    objective_id: ObjectiveId
    violated: bool
    level: Literal["action", "disclosure"] = "action"
    evidence_event_ids: list[int] = Field(default_factory=list)
    detail: str = ""


class Assessment(BaseModel):
    outcome: AttemptOutcome
    verdicts: list[OracleVerdict]
    prevented_event_ids: list[int] = Field(default_factory=list)
    detail: str = ""


class ToolEvidence(BaseModel):
    event_id: int
    kind: str
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    validator: str = ""
    operation_id: str = ""
    provenance: dict[str, str] = Field(default_factory=dict)
