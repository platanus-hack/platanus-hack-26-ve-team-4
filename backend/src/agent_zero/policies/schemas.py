from pydantic import BaseModel, Field

from agent_zero.policies.models import FailureAction, PolicyStatus
from agent_zero.victim.models import ToolName


class PolicyRule(BaseModel):
    validator: str
    on_failure: FailureAction


class PolicyCandidate(BaseModel):
    policy_id: str
    parent_version: int = Field(ge=0)
    finding_ids: list[str] = Field(min_length=1)
    scope: ToolName
    rules: list[PolicyRule] = Field(min_length=1)
    reason: str = Field(min_length=1)
    status: PolicyStatus = PolicyStatus.CANDIDATE
