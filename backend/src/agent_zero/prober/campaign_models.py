from datetime import datetime

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from agent_zero.runtime.utc_datetime import UtcDateTime
from agent_zero.shared.database import AppBase


class Campaign(AppBase):
    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    status: Mapped[str] = mapped_column(String(20))
    max_attempts: Mapped[int]
    attempt_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    case_hashes: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)
