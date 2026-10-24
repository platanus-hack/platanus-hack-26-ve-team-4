from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from agent_zero.events.models import EventType, Visibility


class EventDraft(BaseModel):
    type: EventType
    visibility: Visibility = Visibility.OPERATOR
    attempt_id: str | None = None
    session_id: str | None = None
    policy_version: int | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class TraceEvent(EventDraft):
    id: int
    timestamp: datetime
