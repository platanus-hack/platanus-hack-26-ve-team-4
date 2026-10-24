from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from agent_zero.armor.model_armor import ModelArmor
from agent_zero.config import Settings
from agent_zero.identity.schemas import AgentPrincipal
from agent_zero.memory_bank.memory_cipher import MemoryCipher
from agent_zero.memory_bank.memory_read_service import MemoryReadService
from agent_zero.memory_bank.memory_write_service import MemoryWriteService
from agent_zero.memory_bank.router import router
from agent_zero.shared.database import Database
from agent_zero.telemetry.audit_log import AuditLog
from tests.identity.conftest import FakeClock
from tests.memory_bank.conftest import PrincipalFactory, make_request
from tests.memory_bank.support import ScopeOnlyGuard

SECRET = "secreto-de-prueba"
OPERATOR = {"X-Operator-Secret": SECRET}


@pytest.fixture
def audit_log() -> AuditLog:
    return AuditLog.in_memory()


@pytest.fixture
def api(memory_settings: Settings, audit_log: AuditLog) -> Iterator[TestClient]:
    settings = memory_settings.model_copy(update={"operator_secret": SecretStr(SECRET)})
    database = Database(settings.app_database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await database.create_schema()
        yield
        await database.dispose()

    app = FastAPI(lifespan=lifespan)
    app.state.settings = settings
    app.state.database = database
    app.state.audit_log = audit_log
    app.state.model_armor = ModelArmor()
    app.include_router(router)
    with TestClient(app) as client:
        yield client


async def _seed(
    api: TestClient,
    settings: Settings,
    clock: FakeClock,
    principals: list[AgentPrincipal],
) -> None:
    database: Database = api.app.state.database  # type: ignore[attr-defined]
    cipher = MemoryCipher.from_settings(settings)
    async with database.sessions() as db:
        writer = MemoryWriteService(db, settings, cipher, ScopeOnlyGuard(), clock=clock)
        for principal in principals:
            await writer.write(principal, make_request("dato"))


@pytest.mark.requirement("MEM-04")
def test_route_requires_the_operator_secret(api: TestClient) -> None:
    assert api.post("/api/memory/subjects/cliente-1/forget").status_code == 401
    wrong = {"X-Operator-Secret": "otro"}
    assert api.post("/api/memory/subjects/cliente-1/forget", headers=wrong).status_code == 401


@pytest.mark.requirement("MEM-04")
async def test_operator_erases_subject_across_agents_and_audits_it(
    api: TestClient,
    memory_settings: Settings,
    clock: FakeClock,
    make_principal: PrincipalFactory,
    audit_log: AuditLog,
) -> None:
    principals = [make_principal(), make_principal(agent_id="agent-finanzas")]
    await _seed(api, memory_settings, clock, principals)
    response = api.post("/api/memory/subjects/cliente-1/forget", headers=OPERATOR)
    assert response.status_code == 200
    assert response.json() == {"deleted": 2}
    database: Database = api.app.state.database  # type: ignore[attr-defined]
    cipher = MemoryCipher.from_settings(memory_settings)
    async with database.sessions() as db:
        reader = MemoryReadService(db, cipher, ScopeOnlyGuard(), clock)
        for principal in principals:
            assert await reader.recall(principal, "cliente-1") == []
    [entry] = audit_log.entries()
    assert entry.action == "memory.forget_subject"
    assert entry.attributes == {"deleted": 2}
    assert audit_log.verify().ok


@pytest.mark.requirement("MEM-04", "OBS-03")
def test_audit_entry_redacts_a_pii_subject_id(api: TestClient, audit_log: AuditLog) -> None:
    api.post("/api/memory/subjects/cliente@example.com/forget", headers=OPERATOR)
    [entry] = audit_log.entries()
    assert "example.com" not in entry.resource
