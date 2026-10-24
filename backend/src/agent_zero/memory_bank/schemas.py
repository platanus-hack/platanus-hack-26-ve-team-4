from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from agent_zero.memory_bank.models import MemoryKind


class MemoryItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    agent_id: str
    subject_id: str
    kind: MemoryKind
    content: str
    created_at: datetime
    expires_at: datetime
    source_run_id: str
    source_trace_id: str | None = None


class MemoryWriteRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    subject_id: str = Field(min_length=1, max_length=80)
    kind: MemoryKind
    content: str = Field(min_length=1, max_length=4000)
    source_run_id: str = Field(min_length=1, max_length=80)
    source_trace_id: str | None = Field(default=None, max_length=32)
    ttl_days: int | None = Field(default=None, ge=1)
