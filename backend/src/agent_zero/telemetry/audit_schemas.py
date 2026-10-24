from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

GENESIS_HASH = "0" * 64


class AuditDecision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    ERROR = "error"
    INFO = "info"


class AuditEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    actor: str
    action: str
    resource: str
    decision: AuditDecision
    reason: str = ""
    attributes: dict[str, Any] = Field(default_factory=dict)


class AuditEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    sequence: int = Field(ge=0)
    at: datetime
    actor: str
    action: str
    resource: str
    decision: AuditDecision
    reason: str = ""
    trace_id: str | None = None
    span_id: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    prev_hash: str
    hash: str


class AuditVerification(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    ok: bool
    entries: int
    broken_at: int | None = None
    detail: str = ""
