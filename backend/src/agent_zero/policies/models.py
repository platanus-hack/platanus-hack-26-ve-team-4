from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from agent_zero.runtime.utc_datetime import UtcDateTime
from agent_zero.shared.database import AppBase


class PolicyStatus(StrEnum):
    CANDIDATE = "candidate"
    VALIDATING = "validating"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"


class FailureAction(StrEnum):
    BLOCK = "block"
    DIVERT = "divert"
    QUARANTINE = "quarantine"


class PolicyVersion(AppBase):
    __tablename__ = "policy_versions"

    version: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    parent_version: Mapped[int | None] = mapped_column(nullable=True)
    rules: Mapped[list[str]] = mapped_column(JSON)
    content_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[PolicyStatus] = mapped_column(Enum(PolicyStatus, native_enum=False))
    finding_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    reason: Mapped[str] = mapped_column(Text)
    validation: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)
    activated_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)


class PolicyPointer(AppBase):
    __tablename__ = "policy_pointer"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[int] = mapped_column(Integer)
