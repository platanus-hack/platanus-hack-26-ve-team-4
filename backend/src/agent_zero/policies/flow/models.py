from typing import Any

from sqlalchemy import JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column

from agent_zero.shared.database import AppBase


class FlowPolicyRecord(AppBase):
    __tablename__ = "policy_flow_rules"

    version: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    rules: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    synthesis: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
