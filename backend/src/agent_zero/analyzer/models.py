from datetime import datetime
from enum import StrEnum

from sqlalchemy import JSON, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from agent_zero.runtime.utc_datetime import UtcDateTime
from agent_zero.shared.database import AppBase


class ViolationStatus(StrEnum):
    CONFIRMED = "confirmed"
    NOT_OBSERVED = "not_observed"
    INCONCLUSIVE = "inconclusive"


class FindingStatus(StrEnum):
    OPEN = "open"
    MITIGATED = "mitigated"
    REOPENED = "reopened"


class FindingRecord(AppBase):
    __tablename__ = "findings"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(180), unique=True)
    objective_id: Mapped[str] = mapped_column(String(20))
    tool: Mapped[str] = mapped_column(String(40))
    missing_control: Mapped[str] = mapped_column(String(80))
    affected_policy_version: Mapped[int]
    attempt_ids: Mapped[list[str]] = mapped_column(JSON)
    evidence_event_ids: Mapped[list[int]] = mapped_column(JSON)
    probable_cause: Mapped[str] = mapped_column(Text)
    status: Mapped[FindingStatus] = mapped_column(Enum(FindingStatus, native_enum=False))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime)
