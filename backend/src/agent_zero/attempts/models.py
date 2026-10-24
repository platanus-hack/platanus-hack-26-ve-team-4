from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, Enum, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from agent_zero.routing.models import Route
from agent_zero.runtime.utc_datetime import UtcDateTime
from agent_zero.shared.database import AppBase


class AttemptStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    EVALUATED = "evaluated"
    INCONCLUSIVE = "inconclusive"

    @property
    def open(self) -> bool:
        return self in (AttemptStatus.QUEUED, AttemptStatus.RUNNING)


class AttemptOutcome(StrEnum):
    CONFIRMED_VIOLATION = "confirmed_violation"
    PREVENTED = "prevented"
    NOT_ACHIEVED = "not_achieved"
    CONTAINED_HONEYPOT = "contained_honeypot"
    INCONCLUSIVE = "inconclusive"


class AttemptOrigin(StrEnum):
    AUDIENCE = "audience"
    AUTONOMOUS = "autonomous"


class Attempt(AppBase):
    __tablename__ = "attempts"
    __table_args__ = (UniqueConstraint("session_id", "idempotency_key"),)

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(32), index=True)
    origin: Mapped[AttemptOrigin] = mapped_column(Enum(AttemptOrigin, native_enum=False, length=16))
    idempotency_key: Mapped[str] = mapped_column(String(120))
    messages: Mapped[list[str]] = mapped_column(JSON)
    objective_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    policy_version: Mapped[int] = mapped_column(Integer)
    route: Mapped[Route] = mapped_column(Enum(Route, native_enum=False, length=16))
    run_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[AttemptStatus] = mapped_column(Enum(AttemptStatus, native_enum=False, length=16))
    outcome: Mapped[AttemptOutcome | None] = mapped_column(
        Enum(AttemptOutcome, native_enum=False, length=24), nullable=True
    )
    reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, index=True)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime)
