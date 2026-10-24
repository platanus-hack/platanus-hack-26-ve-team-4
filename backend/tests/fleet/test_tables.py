from pathlib import Path

from sqlalchemy import inspect

from agent_zero.fleet.tables import FLEET_TABLES, create_fleet_schema
from agent_zero.shared.database import Database


async def test_creates_every_fleet_table(tmp_path: Path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'tablas.db'}")
    await create_fleet_schema(database)
    async with database.engine.connect() as connection:
        names = await connection.run_sync(lambda sync: set(inspect(sync).get_table_names()))
    await database.dispose()
    assert {model.__tablename__ for model in FLEET_TABLES} <= names
