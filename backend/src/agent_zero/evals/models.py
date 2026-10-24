from datetime import datetime
from typing import Any

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from agent_zero.runtime.utc_datetime import UtcDateTime
from agent_zero.shared.database import AppBase


class Evaluation(AppBase):
    __tablename__ = "evaluations"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    status: Mapped[str] = mapped_column(String(20))
    before_version: Mapped[int]
    after_version: Mapped[int]
    repetitions: Mapped[int]
    max_calls: Mapped[int]
    cases: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    report: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    stop_reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)
    finished_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)


class EvaluationExecution(AppBase):
    __tablename__ = "evaluation_executions"

    evaluation_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    ordinal: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(String(20))
    starts: Mapped[int] = mapped_column(default=0)
    result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
