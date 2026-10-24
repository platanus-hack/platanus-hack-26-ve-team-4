from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from agent_zero.config import Settings
from agent_zero.shared.database import Database
from tests.identity.conftest import FakeClock


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def fleet_settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path,
        environment="test",
        operator_secret="secreto-de-prueba",
        identity_signing_key="clave-de-prueba",
        otel_exporter="memory",
        runtime_poll_seconds=0.01,
        allowed_data_regions=["cl"],
    )


@pytest.fixture
async def database(fleet_settings: Settings) -> AsyncIterator[Database]:
    db = Database(fleet_settings.app_database_url)
    await db.create_schema()
    yield db
    await db.dispose()
