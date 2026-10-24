from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent_zero.config import Settings
from agent_zero.llm.models import ModelRole
from agent_zero.registry.router import router
from agent_zero.registry.schemas import AgentManifest, ToolGrant
from agent_zero.shared.classification import DataClassification
from agent_zero.shared.database import Database

SECRET = "secreto-de-prueba"


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
def registry_settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path, environment="test", operator_secret=SECRET)


@pytest.fixture
async def database(registry_settings: Settings) -> AsyncIterator[Database]:
    db = Database(registry_settings.app_database_url)
    await db.create_schema()
    yield db
    await db.dispose()


@pytest.fixture
def make_manifest() -> Callable[..., AgentManifest]:
    def build(**overrides: Any) -> AgentManifest:
        fields: dict[str, Any] = {
            "agent_id": "agente-finanzas",
            "version": "1.0.0",
            "display_name": "Agente de Finanzas",
            "department": "finanzas",
            "description": "Concilia facturas y pagos.",
            "capabilities": ("conciliacion", "facturacion"),
            "tags": ("contabilidad",),
            "model_role": ModelRole.VICTIM,
            "system_prompt": "Eres un asistente de finanzas. Responde con precisión.",
            "tools": (
                ToolGrant(
                    name="get_invoice",
                    description="Obtiene una factura por número.",
                    classification=DataClassification.CONFIDENTIAL,
                ),
            ),
            "scopes": ("tool:get_invoice", "memory:read"),
            "max_classification": DataClassification.CONFIDENTIAL,
            "allowed_regions": ("cl",),
        }
        fields.update(overrides)
        return AgentManifest(**fields)

    return build


@pytest.fixture
def api(registry_settings: Settings) -> Iterator[TestClient]:
    database = Database(registry_settings.app_database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await database.create_schema()
        yield
        await database.dispose()

    app = FastAPI(lifespan=lifespan)
    app.state.settings = registry_settings
    app.state.database = database
    app.include_router(router)
    with TestClient(app) as client:
        yield client


@pytest.fixture
def operator() -> dict[str, str]:
    return {"X-Operator-Secret": SECRET}
