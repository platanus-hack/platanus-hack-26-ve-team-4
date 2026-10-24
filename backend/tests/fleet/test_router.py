from pathlib import Path

from fastapi.testclient import TestClient
from pydantic import SecretStr

from agent_zero.config import Settings
from agent_zero.main import create_app

SECRET = "secreto-de-operador-para-pruebas"


def client_for(tmp_path: Path, exporter: str = "memory") -> TestClient:
    settings = Settings(
        data_dir=tmp_path,
        environment="test",
        operator_secret=SecretStr(SECRET),
        otel_exporter=exporter,
    )
    return TestClient(create_app(settings))


def test_fleet_routes_require_the_operator_secret(tmp_path: Path) -> None:
    with client_for(tmp_path) as client:
        assert client.get("/api/fleet/status").status_code == 401


def test_status_lists_the_victim_handler_and_tools(tmp_path: Path) -> None:
    with client_for(tmp_path) as client:
        status = client.get("/api/fleet/status", headers={"x-operator-secret": SECRET}).json()

    assert status["handlers"] == ["support_conversation"]
    assert status["tools"] == ["get_order", "request_refund", "search_knowledge"]
    assert status["llm_mode"] == "offline"


def test_trace_needs_the_memory_exporter(tmp_path: Path) -> None:
    with client_for(tmp_path, "none") as client:
        response = client.get("/api/fleet/runs/run-x/trace", headers={"x-operator-secret": SECRET})

    assert response.status_code == 409


def test_empty_audit_verifies(tmp_path: Path) -> None:
    with client_for(tmp_path) as client:
        report = client.get("/api/fleet/audit", headers={"x-operator-secret": SECRET}).json()

    assert report["verification"]["ok"] is True
    assert report["latest"] == []
