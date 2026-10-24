from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from agent_zero.config import Settings
from agent_zero.identity.schemas import AgentGrant
from agent_zero.shared.classification import DataClassification
from agent_zero.shared.database import Database


class FakeClock:
    def __init__(self) -> None:
        self.now = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: int) -> None:
        self.now += timedelta(seconds=seconds)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def identity_settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path,
        environment="test",
        identity_signing_key="clave-de-prueba",
        identity_token_ttl_seconds=900,
    )


@pytest.fixture
async def database(identity_settings: Settings) -> AsyncIterator[Database]:
    db = Database(identity_settings.app_database_url)
    await db.create_schema()
    yield db
    await db.dispose()


@pytest.fixture
def grant() -> AgentGrant:
    return AgentGrant(
        agent_id="agent-soporte",
        version="1.0.0",
        department="soporte",
        scopes=("tool:get_order", "memory:read", "memory:write"),
        clearance=DataClassification.INTERNAL,
        allowed_regions=("cl",),
    )
