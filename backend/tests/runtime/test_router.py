from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from agent_zero.config import Settings
from agent_zero.runtime.handler_registry import HandlerRegistry
from agent_zero.runtime.router import router
from agent_zero.runtime.run_worker import RunWorker
from agent_zero.runtime.wiring import RuntimeWiring
from agent_zero.shared.database import Database
from tests.runtime.flows import drain, finish, wait_two_weeks
from tests.runtime.support import FakeAdmission, FakeClock, ScriptedHandler


@pytest.fixture
async def api(
    database: Database,
    registry: HandlerRegistry,
    clock: FakeClock,
    tmp_path: Path,
) -> AsyncIterator[httpx.AsyncClient]:
    registry.register(ScriptedHandler("rapido", [finish]))
    registry.register(ScriptedHandler("lento", [wait_two_weeks, finish]))
    app = FastAPI()
    app.state.database = database
    app.state.handler_registry = registry
    app.state.runtime_clock = clock
    app.include_router(router)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        yield client


def body(handler: str, key: str | None = None) -> dict[str, object]:
    return {
        "agent_id": "agente-soporte",
        "agent_version": "1.0.0",
        "handler": handler,
        "input": {"pedido": 7},
        "idempotency_key": key,
    }


@pytest.mark.requirement("RUN-01")
async def test_post_returns_202_and_run_succeeds_in_background(
    api: httpx.AsyncClient,
    database: Database,
    registry: HandlerRegistry,
    runtime_settings: Settings,
    clock: FakeClock,
) -> None:
    response = await api.post("/api/runtime/runs", json=body("rapido"))
    assert response.status_code == 202
    run_id = response.json()["run_id"]
    assert response.json()["status"] == "queued"
    await drain(
        RunWorker(
            RuntimeWiring(database.sessions, registry, FakeAdmission(), clock), runtime_settings
        )
    )
    state = await api.get(f"/api/runtime/runs/{run_id}")
    assert state.status_code == 200
    assert state.json()["status"] == "succeeded"


@pytest.mark.requirement("RUN-03")
async def test_idempotent_post_and_cancel(api: httpx.AsyncClient) -> None:
    first = await api.post("/api/runtime/runs", json=body("lento", "clave-1"))
    second = await api.post("/api/runtime/runs", json=body("lento", "clave-1"))
    assert first.json()["run_id"] == second.json()["run_id"]
    cancelled = await api.post(f"/api/runtime/runs/{first.json()['run_id']}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"


async def test_error_responses(api: httpx.AsyncClient) -> None:
    assert (await api.post("/api/runtime/runs", json=body("nadie"))).status_code == 422
    assert (await api.get("/api/runtime/runs/run-x")).status_code == 404
    assert (await api.post("/api/runtime/runs/run-x/cancel")).status_code == 404
    assert (await api.post("/api/runtime/runs", json={"agent_id": "a"})).status_code == 422
