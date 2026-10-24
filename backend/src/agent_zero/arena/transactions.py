from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def serialize_write(db: AsyncSession) -> None:
    """Acquire SQLite's writer reservation before reading admission or control state.

    A process-local asyncio lock cannot serialize multiple API/worker processes. All
    decisions that read then mutate arena state use this database transaction too.
    The caller owns commit/rollback; acquire it before the first database read.
    """
    if db.in_transaction():
        raise RuntimeError("La reserva de escritura debe preceder las lecturas.")
    await db.execute(text("BEGIN IMMEDIATE"))
