from datetime import datetime
from typing import Any

from sqlalchemy import JSON, String, Text
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


class CampaignPlan(AppBase):
    __tablename__ = "campaign_plans"

    campaign_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    generation: Mapped[str] = mapped_column(String(20), default="templates")
    max_mutations: Mapped[int] = mapped_column(default=30)
    generation_calls: Mapped[int] = mapped_column(default=0)
    stop_reason: Mapped[str] = mapped_column(Text, default="")


class CampaignCaseRecord(AppBase):
    __tablename__ = "campaign_cases"

    campaign_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    index: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(String(30))
    customer_id: Mapped[str] = mapped_column(String(40))
    case_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    digest: Mapped[str] = mapped_column(String(64))
    session_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    attempt_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    error: Mapped[str] = mapped_column(Text, default="")
