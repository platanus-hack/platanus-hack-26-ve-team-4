from typing import Any

from sqlalchemy import JSON, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class StoreBase(DeclarativeBase):
    pass


class StoreOrder(StoreBase):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON)
    refunded_cents: Mapped[int] = mapped_column(Integer, default=0)


class StoreRefund(StoreBase):
    __tablename__ = "refunds"

    operation_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    order_id: Mapped[str] = mapped_column(String(40))
    amount_cents: Mapped[int] = mapped_column(Integer)
    attempt_id: Mapped[str] = mapped_column(String(40), index=True)


class StoreOperation(StoreBase):
    __tablename__ = "operations"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    output: Mapped[str] = mapped_column(Text)
    fingerprint: Mapped[str] = mapped_column(String(64))


class ControlledFixtureRecord(StoreBase):
    __tablename__ = "controlled_fixtures"

    session_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    surface: Mapped[str] = mapped_column(String(20), primary_key=True)
    target_tool: Mapped[str] = mapped_column(String(40), primary_key=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON)
