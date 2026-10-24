from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from agent_zero.runtime.models import RunStatus


class RunCreate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    agent_id: str = Field(min_length=1, max_length=80)
    agent_version: str = Field(min_length=1, max_length=40)
    handler: str = Field(min_length=1, max_length=80)
    input: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=120)


class RunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)

    run_id: str
    agent_id: str
    agent_version: str
    handler: str
    status: RunStatus
    attempts: int
    step_index: int
    resume_at: datetime | None
    checkpoint_json: dict[str, Any]
    output_json: dict[str, Any] | None
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime


class RunAccepted(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    status: RunStatus
