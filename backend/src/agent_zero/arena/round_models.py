from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from agent_zero.runtime.utc_datetime import UtcDateTime
from agent_zero.shared.database import AppBase


class RoundMetadata(AppBase):
    __tablename__ = "arena_round_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    round_id: Mapped[str] = mapped_column(String(40), unique=True)
    started_at: Mapped[datetime] = mapped_column(UtcDateTime)
    first_event_id: Mapped[int] = mapped_column(Integer, default=0)


class RoundArchive(AppBase):
    __tablename__ = "arena_round_archives"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    round_id: Mapped[str] = mapped_column(String(40), unique=True)
    next_round_id: Mapped[str] = mapped_column(String(40))
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20))
    content_hash: Mapped[str] = mapped_column(String(64))
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)
    completed_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
