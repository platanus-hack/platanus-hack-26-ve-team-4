from datetime import timedelta

from fastapi.testclient import TestClient

from agent_zero.config import Settings
from agent_zero.sessions.session_token import SessionTokenCodec

NEW_SESSION = {"alias": "  neo  ", "accepted_rules": True}


def test_create_session_returns_public_projection_with_token(client: TestClient) -> None:
    response = client.post("/api/sessions", json=NEW_SESSION)

    assert response.status_code == 201
    body = response.json()
    assert body["id"].startswith("sess-")
    assert body["alias"] == "neo"
    assert set(body) == {"id", "alias", "created_at", "token", "expires_at"}


def test_create_session_rejects_invalid_alias(client: TestClient) -> None:
    response = client.post("/api/sessions", json={"alias": "<script>", "accepted_rules": True})

    assert response.status_code == 422


def test_create_session_requires_accepting_the_rules(client: TestClient) -> None:
    assert client.post("/api/sessions", json={"alias": "neo"}).status_code == 422
    rejected = client.post("/api/sessions", json={"alias": "neo", "accepted_rules": False})
    assert rejected.status_code == 422


def test_client_cannot_choose_its_customer_identity(client: TestClient) -> None:
    response = client.post("/api/sessions", json={**NEW_SESSION, "customer_id": "cust-ana"})

    assert response.status_code == 422


def test_token_resolves_its_own_session(client: TestClient) -> None:
    created = client.post("/api/sessions", json=NEW_SESSION).json()

    response = client.get(
        "/api/sessions/me", headers={"Authorization": f"Bearer {created['token']}"}
    )

    assert response.status_code == 200
    assert response.json() == {key: created[key] for key in ("id", "alias", "created_at")}


def test_valid_token_for_a_removed_session_is_rejected(
    client: TestClient, settings: Settings
) -> None:
    codec = SessionTokenCodec(
        settings.session_signing_key.get_secret_value().encode("utf-8"), timedelta(hours=1)
    )
    token = codec.issue("sess-borrada").token

    response = client.get("/api/sessions/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["detail"] == "La sesión ya no existe."


def test_me_needs_a_valid_token(client: TestClient) -> None:
    token = client.post("/api/sessions", json=NEW_SESSION).json()["token"]
    payload, signature = token.split(".")
    tampered = f"{payload[:-1]}{'A' if payload[-1] != 'A' else 'B'}.{signature}"

    assert client.get("/api/sessions/me").status_code == 401
    for bad in (tampered, "no-es-un-token", f"{payload}."):
        response = client.get("/api/sessions/me", headers={"Authorization": f"Bearer {bad}"})
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"
