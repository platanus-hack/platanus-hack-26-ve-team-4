from datetime import UTC, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Mapped, mapped_column

from agent_zero.runtime.utc_datetime import UtcDateTime
from agent_zero.shared.database import AppBase, Database


class Stamp(AppBase):
    __tablename__ = "test_utc_stamps"

    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)


async def test_round_trip_returns_aware_utc(database: Database) -> None:
    await database.create_schema()
    offset = timezone(timedelta(hours=-4))
    async with database.sessions() as db:
        db.add(Stamp(id=1, at=datetime(2026, 10, 24, 8, 0, tzinfo=offset)))
        db.add(Stamp(id=2, at=datetime(2026, 10, 24, 12, 0)))
        db.add(Stamp(id=3, at=None))
        await db.commit()
    async with database.sessions() as db:
        rows = (await db.execute(select(Stamp).order_by(Stamp.id))).scalars().all()
    assert rows[0].at == datetime(2026, 10, 24, 12, 0, tzinfo=UTC)
    assert rows[1].at == datetime(2026, 10, 24, 12, 0, tzinfo=UTC)
    assert rows[2].at is None
