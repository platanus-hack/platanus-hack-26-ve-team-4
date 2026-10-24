from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from agent_zero.config import Settings
from agent_zero.shared.database import Database
from tests.agent_gateway.support import Harness, build_harness
from tests.identity.conftest import FakeClock


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def gateway_settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path,
        environment="test",
        identity_signing_key="clave-de-prueba",
        allowed_data_regions=["cl"],
        gateway_rate_limit_per_minute=3,
    )


@pytest.fixture
async def database(gateway_settings: Settings) -> AsyncIterator[Database]:
    db = Database(gateway_settings.app_database_url)
    await db.create_schema()
    yield db
    await db.dispose()


@pytest.fixture
def harness(gateway_settings: Settings, database: Database, clock: FakeClock) -> Harness:
    return build_harness(gateway_settings, database, clock)
