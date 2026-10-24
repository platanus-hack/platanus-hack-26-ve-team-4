from collections.abc import AsyncIterator, Callable
from pathlib import Path

import pytest

from agent_zero.config import Settings
from agent_zero.identity.schemas import AgentPrincipal
from agent_zero.memory_bank.memory_cipher import MemoryCipher
from agent_zero.memory_bank.models import MemoryKind
from agent_zero.memory_bank.schemas import MemoryWriteRequest
from agent_zero.shared.classification import DataClassification
from agent_zero.shared.database import Database
from tests.identity.conftest import FakeClock

PrincipalFactory = Callable[..., AgentPrincipal]


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def memory_settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path, environment="test", memory_default_ttl_days=30)


@pytest.fixture
def cipher(memory_settings: Settings) -> MemoryCipher:
    return MemoryCipher.from_settings(memory_settings)


@pytest.fixture
async def database(memory_settings: Settings) -> AsyncIterator[Database]:
    db = Database(memory_settings.app_database_url)
    await db.create_schema()
    yield db
    await db.dispose()


@pytest.fixture
def make_principal(clock: FakeClock) -> PrincipalFactory:
    def factory(
        agent_id: str = "agent-soporte",
        scopes: tuple[str, ...] = ("memory:read", "memory:write"),
    ) -> AgentPrincipal:
        return AgentPrincipal(
            credential_id="cred-1",
            agent_id=agent_id,
            version="1.0.0",
            department="soporte",
            scopes=scopes,
            clearance=DataClassification.INTERNAL,
            allowed_regions=("cl",),
            issued_at=clock(),
            expires_at=clock(),
        )

    return factory


def make_request(
    content: str = "Prefiere entregas por la tarde",
    subject_id: str = "cliente-1",
    run_id: str = "run-1",
    kind: MemoryKind = MemoryKind.PREFERENCE,
    ttl_days: int | None = None,
) -> MemoryWriteRequest:
    return MemoryWriteRequest(
        subject_id=subject_id,
        kind=kind,
        content=content,
        source_run_id=run_id,
        ttl_days=ttl_days,
    )
