from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agent_zero.config import Settings
from agent_zero.main import create_app

OPERATOR_SECRET = "secreto-de-operador-de-prueba"
NEW_SESSION = {"alias": "trinity", "accepted_rules": True}


@pytest.fixture
def api(tmp_path: Path) -> Iterator[TestClient]:
    settings = Settings(data_dir=tmp_path, environment="test", operator_secret=OPERATOR_SECRET)
    with TestClient(create_app(settings)) as client:
        yield client


def test_operator_lists_sessions_with_their_real_identity_and_route(api: TestClient) -> None:
    created = api.post("/api/sessions", json=NEW_SESSION).json()

    response = api.get("/api/operator/sessions", headers={"X-Operator-Secret": OPERATOR_SECRET})

    assert response.status_code == 200
    [session] = response.json()
    assert session["id"] == created["id"]
    assert session["customer_id"].startswith("cust-")
    assert session["route"] == "protected"


def test_operator_routes_reject_missing_or_wrong_secret(api: TestClient) -> None:
    assert api.get("/api/operator/sessions").status_code == 401
    wrong = {"X-Operator-Secret": "otro"}
    assert api.get("/api/operator/sessions", headers=wrong).status_code == 401


def test_audience_token_cannot_read_operation(api: TestClient) -> None:
    token = api.post("/api/sessions", json=NEW_SESSION).json()["token"]

    as_bearer = {"Authorization": f"Bearer {token}"}
    assert api.get("/api/operator/sessions", headers=as_bearer).status_code == 401
    as_secret = {"X-Operator-Secret": token}
    assert api.get("/api/operator/sessions", headers=as_secret).status_code == 401


def test_audience_token_cannot_approve_or_activate(api: TestClient) -> None:
    token = api.post("/api/sessions", json=NEW_SESSION).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    approve = api.post("/api/registry/agents/soporte/versions/1.0.0/approve", headers=headers)
    assert approve.status_code == 401
    assert api.post("/api/runtime/runs", json={}, headers=headers).status_code == 401


def test_operator_secret_is_not_a_session_token(api: TestClient) -> None:
    response = api.get("/api/sessions/me", headers={"Authorization": f"Bearer {OPERATOR_SECRET}"})

    assert response.status_code == 401
