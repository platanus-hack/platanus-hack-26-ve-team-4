from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from agent_zero.runtime.utc_datetime import UtcDateTime
from agent_zero.shared.database import AppBase


class EventType(StrEnum):
    ROUND_STARTED = "round_started"
    ATTEMPT_QUEUED = "attempt_queued"
    ATTEMPT_STARTED = "attempt_started"
    ATTEMPT_COMPLETED = "attempt_completed"
    TOOL_PROPOSED = "tool_proposed"
    TOOL_DENIED = "tool_denied"
    TOOL_COMPLETED = "tool_completed"
    ROUTE_CHANGED = "route_changed"
    ATTEMPT_EVALUATED = "attempt_evaluated"
    FINDING_OPENED = "finding_opened"
    PATCH_PROPOSED = "patch_proposed"
    PATCH_VALIDATED = "patch_validated"
    POLICY_ACTIVATED = "policy_activated"
    POLICY_ROLLED_BACK = "policy_rolled_back"
    PROBE_ROUND_CLOSED = "probe_round_closed"


class Visibility(StrEnum):
    PUBLIC = "public"
    OPERATOR = "operator"


class EventRecord(AppBase):
    __tablename__ = "product_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[EventType] = mapped_column(Enum(EventType, native_enum=False))
    visibility: Mapped[Visibility] = mapped_column(Enum(Visibility, native_enum=False))
    attempt_id: Mapped[str | None] = mapped_column(String(40), index=True, nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    policy_version: Mapped[int | None] = mapped_column(nullable=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON)
    timestamp: Mapped[datetime] = mapped_column(UtcDateTime)
    dedup_key: Mapped[str | None] = mapped_column(String(180), unique=True, nullable=True)


class EventDelivery(AppBase):
    __tablename__ = "product_event_delivery"

    event_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    delivered_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
