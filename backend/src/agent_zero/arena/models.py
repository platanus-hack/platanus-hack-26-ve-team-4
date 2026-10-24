from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from agent_zero.shared.database import AppBase


class ArenaState(AppBase):
    __tablename__ = "arena_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    accepting: Mapped[bool] = mapped_column(default=True)
    revealed: Mapped[bool] = mapped_column(default=False)
