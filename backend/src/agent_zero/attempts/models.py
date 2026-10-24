from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, Enum, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from agent_zero.routing.models import Route
from agent_zero.runtime.utc_datetime import UtcDateTime
from agent_zero.shared.database import AppBase


class AttemptStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    EVALUATED = "evaluated"
    INCONCLUSIVE = "inconclusive"


class AttemptOutcome(StrEnum):
    CONFIRMED_VIOLATION = "confirmed_violation"
    PREVENTED = "prevented"
    NOT_ACHIEVED = "not_achieved"
    CONTAINED_HONEYPOT = "contained_honeypot"
    INCONCLUSIVE = "inconclusive"


class Attempt(AppBase):
    __tablename__ = "attempts"
    __table_args__ = (UniqueConstraint("session_id", "idempotency_key"),)

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(40), index=True)
    origin: Mapped[str] = mapped_column(String(20), default="audience")
    campaign_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    policy_version: Mapped[int]
    route: Mapped[Route] = mapped_column(Enum(Route, native_enum=False))
    run_id: Mapped[str] = mapped_column(String(40), unique=True)
    idempotency_key: Mapped[str] = mapped_column(String(120))
    messages: Mapped[list[str]] = mapped_column(JSON)
    customer_id: Mapped[str] = mapped_column(String(40))
    objective_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[AttemptStatus] = mapped_column(Enum(AttemptStatus, native_enum=False))
    outcome: Mapped[AttemptOutcome | None] = mapped_column(
        Enum(AttemptOutcome, native_enum=False), nullable=True
    )
    reply: Mapped[str] = mapped_column(Text, default="")
    assessment: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    defense_processed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime)
