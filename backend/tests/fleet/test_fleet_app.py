import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agent_zero.config import Settings
from agent_zero.main import create_app
from agent_zero.runtime.handlers import StepContext
from agent_zero.runtime.step_results import Complete, StepResult
from tests.agent_gateway.support import build_manifest

OPERATOR = {"X-Operator-Secret": "secreto-de-prueba"}


class EchoHandler:
    name = "eco"

    async def step(self, context: StepContext) -> StepResult:
        return Complete(output={"agent": context.principal.agent_id})


@pytest.fixture
def fleet_client(tmp_path: Path) -> Iterator[TestClient]:
    settings = Settings(
        data_dir=tmp_path,
        environment="test",
        operator_secret="secreto-de-prueba",
        runtime_poll_seconds=0.01,
    )
    with TestClient(create_app(settings)) as client:
        yield client


def test_fleet_is_wired_into_the_app(fleet_client: TestClient) -> None:
    app = fleet_client.app
    assert app.state.fleet.worker is not None  # type: ignore[attr-defined]
    assert fleet_client.get("/api/registry/agents").json() == []
    assert fleet_client.get("/health").status_code == 200


def test_runtime_routes_require_the_operator_secret(fleet_client: TestClient) -> None:
    body = {"agent_id": "agente-soporte", "agent_version": "1.0.0", "handler": "eco"}
    assert fleet_client.post("/api/runtime/runs", json=body).status_code == 401
    unknown = fleet_client.post("/api/runtime/runs", json=body, headers=OPERATOR)
    assert unknown.status_code == 422


@pytest.mark.requirement("RUN-01", "REG-03", "RUN-04")
def test_http_run_reaches_succeeded_in_the_background(fleet_client: TestClient) -> None:
    fleet_client.app.state.handler_registry.register(EchoHandler())  # type: ignore[attr-defined]
    manifest = build_manifest().model_dump(mode="json")
    assert (
        fleet_client.post("/api/registry/agents", json=manifest, headers=OPERATOR).status_code
        == 201
    )
    approval = fleet_client.post(
        "/api/registry/agents/agente-soporte/versions/1.0.0/approve",
        json={"approved_by": "operador"},
        headers=OPERATOR,
    )
    assert approval.status_code == 200
    body = {"agent_id": "agente-soporte", "agent_version": "1.0.0", "handler": "eco"}
    accepted = fleet_client.post("/api/runtime/runs", json=body, headers=OPERATOR)
    assert accepted.status_code == 202
    run_id = accepted.json()["run_id"]
    state = {}
    for _ in range(200):
        state = fleet_client.get(f"/api/runtime/runs/{run_id}", headers=OPERATOR).json()
        if state["status"] == "succeeded":
            break
        time.sleep(0.01)
    assert state["status"] == "succeeded"
    assert state["output_json"] == {"agent": "agente-soporte"}


@pytest.mark.requirement("RUN-04")
def test_http_run_of_an_unapproved_agent_fails(fleet_client: TestClient) -> None:
    fleet_client.app.state.handler_registry.register(EchoHandler())  # type: ignore[attr-defined]
    body = {"agent_id": "agente-fantasma", "agent_version": "1.0.0", "handler": "eco"}
    run_id = fleet_client.post("/api/runtime/runs", json=body, headers=OPERATOR).json()["run_id"]
    state = {}
    for _ in range(200):
        state = fleet_client.get(f"/api/runtime/runs/{run_id}", headers=OPERATOR).json()
        if state["status"] == "failed":
            break
        time.sleep(0.01)
    assert state["status"] == "failed"
    assert state["failure_reason"].startswith("admisión denegada:")


@pytest.mark.requirement("MEM-04")
def test_memory_erasure_route_is_wired_and_operator_only(fleet_client: TestClient) -> None:
    path = "/api/memory/subjects/cliente-1/forget"
    assert fleet_client.post(path).status_code == 401
    erased = fleet_client.post(path, headers=OPERATOR)
    assert erased.status_code == 200
    assert erased.json() == {"deleted": 0}
    entries = fleet_client.app.state.audit_log.entries()  # type: ignore[attr-defined]
    assert entries[-1].action == "memory.forget_subject"
