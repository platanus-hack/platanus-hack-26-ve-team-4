from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from agent_zero.shared.database import AppBase


class MemoryKind(StrEnum):
    FACT = "fact"
    PREFERENCE = "preference"
    EVENT = "event"
    SUMMARY = "summary"


class MemoryRecord(AppBase):
    __tablename__ = "memory_records"
    __table_args__ = (Index("ix_memory_records_owner", "agent_id", "subject_id"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    agent_id: Mapped[str] = mapped_column(String(80))
    subject_id: Mapped[str] = mapped_column(String(80))
    kind: Mapped[MemoryKind] = mapped_column(Enum(MemoryKind, native_enum=False, length=16))
    ciphertext: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_run_id: Mapped[str] = mapped_column(String(80))
    source_trace_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
