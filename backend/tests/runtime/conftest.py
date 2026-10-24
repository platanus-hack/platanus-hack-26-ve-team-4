from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from agent_zero.config import Settings
from agent_zero.runtime.handler_registry import HandlerRegistry
from agent_zero.runtime.models import Run
from agent_zero.shared.database import Database
from tests.runtime.support import FakeAdmission, FakeClock

REGISTERED_TABLES = (Run,)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def runtime_settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path,
        environment="test",
        runtime_max_attempts=3,
        runtime_worker_concurrency=2,
        runtime_poll_seconds=0.01,
    )


@pytest.fixture
async def database(runtime_settings: Settings) -> AsyncIterator[Database]:
    db = Database(runtime_settings.app_database_url)
    await db.create_schema()
    yield db
    await db.dispose()


@pytest.fixture
def registry() -> HandlerRegistry:
    return HandlerRegistry()


@pytest.fixture
def admission() -> FakeAdmission:
    return FakeAdmission()
