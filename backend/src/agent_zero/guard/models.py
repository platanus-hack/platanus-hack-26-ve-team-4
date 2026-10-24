from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from agent_zero.shared.database import AppBase


def _now() -> datetime:
    return datetime.now(UTC)


class GuardCallRecord(AppBase):
    __tablename__ = "guard_calls"

    call_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    contract_id: Mapped[str] = mapped_column(String(64), index=True)
    tool: Mapped[str] = mapped_column(String(64))
    subject: Mapped[str] = mapped_column(String(128))
    facts: Mapped[dict[str, Any]] = mapped_column(JSON)
    allowed: Mapped[bool] = mapped_column(Boolean)
    rule_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    policy_version: Mapped[int] = mapped_column(Integer)
    effect: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class GuardPolicyRecord(AppBase):
    __tablename__ = "guard_policies"
    __table_args__ = (UniqueConstraint("contract_id", "version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contract_id: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[int] = mapped_column(Integer)
    parent_version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16))
    rules: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    report: Mapped[dict[str, Any]] = mapped_column(JSON)
    finding_id: Mapped[str] = mapped_column(String(40))
    contract_digest: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class GuardFindingRecord(AppBase):
    __tablename__ = "guard_findings"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    contract_id: Mapped[str] = mapped_column(String(64), index=True)
    call_id: Mapped[str] = mapped_column(String(40))
    invariant_ids: Mapped[list[str]] = mapped_column(JSON)
    policy_version: Mapped[int] = mapped_column(Integer)
    resolved_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class GuardContractRecord(AppBase):
    __tablename__ = "guard_contracts"

    contract_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    version: Mapped[str] = mapped_column(String(20))
    source: Mapped[str] = mapped_column(Text)
    digest: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
