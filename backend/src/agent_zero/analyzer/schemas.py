from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from agent_zero.analyzer.models import FindingStatus, ViolationStatus
from agent_zero.prober.models import AttackFamily
from agent_zero.routing.models import Route


class AttemptAssessment(BaseModel):
    attempt_id: str
    attack_family: AttackFamily | None
    violation_status: ViolationStatus
    route: Route
    confidence: float = Field(ge=0.0, le=1.0)


class Finding(BaseModel):
    finding_id: str
    objective_id: str
    affected_policy_version: int
    reproduction_case_ids: list[str] = Field(min_length=1)
    evidence_event_ids: list[int]
    probable_cause: str
    confidence: float = Field(ge=0.0, le=1.0)
    status: FindingStatus = FindingStatus.OPEN


class FindingAnalysis(BaseModel):
    """Advisory text only. The schema cannot encode verdicts or policy changes."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    attack_family: AttackFamily
    probable_cause: str = Field(min_length=1, max_length=1500)
    reproduction_steps: list[Annotated[str, Field(min_length=1, max_length=500)]] = Field(
        min_length=1, max_length=6
    )
    limitations: str = Field(min_length=1, max_length=1000)
