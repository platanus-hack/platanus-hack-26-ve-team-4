import asyncio
import os
import secrets
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from agent_zero.config import Settings
from agent_zero.main import create_app
from agent_zero.shared.database import ensure_database

# With a postgresql+asyncpg URL, every test that uses `settings` gets its own fresh databases.
POSTGRES_URL = os.environ.get("AGENT_ZERO_TEST_DATABASE_URL")


async def _create_databases(url: str, names: list[str]) -> None:
    for name in names:
        await ensure_database(make_url(url).set(database=name).render_as_string(False))


async def _drop_databases(url: str, names: list[str]) -> None:
    admin = create_async_engine(
        make_url(url).set(database="postgres"), isolation_level="AUTOCOMMIT"
    )
    try:
        async with admin.connect() as connection:
            for name in names:
                await connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
    finally:
        await admin.dispose()


@pytest.fixture
def settings(tmp_path: Path) -> Iterator[Settings]:
    if POSTGRES_URL is None:
        yield Settings(data_dir=tmp_path, environment="test")
        return
    name = f"az_test_{secrets.token_hex(6)}"
    names = [name, f"{name}_protected", f"{name}_honeypot"]
    # Created up front because some tests build their Database without the app lifespan.
    asyncio.run(_create_databases(POSTGRES_URL, names))
    url = make_url(POSTGRES_URL).set(database=name).render_as_string(hide_password=False)
    yield Settings(data_dir=tmp_path, environment="test", database_url=SecretStr(url))
    asyncio.run(_drop_databases(POSTGRES_URL, names))


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as test_client:
        yield test_client
