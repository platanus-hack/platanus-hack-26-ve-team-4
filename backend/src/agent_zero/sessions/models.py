from datetime import datetime

from sqlalchemy import DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from agent_zero.routing.models import Route
from agent_zero.shared.database import AppBase


class ArenaSession(AppBase):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    alias: Mapped[str] = mapped_column(String(40))
    customer_id: Mapped[str] = mapped_column(String(32))
    route: Mapped[Route] = mapped_column(Enum(Route, native_enum=False, length=16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
