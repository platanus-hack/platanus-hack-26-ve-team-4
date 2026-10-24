from fastapi.testclient import TestClient


def test_create_session_returns_public_projection(client: TestClient) -> None:
    response = client.post("/api/sessions", json={"alias": "  neo  ", "accepted_rules": True})

    assert response.status_code == 201
    body = response.json()
    assert body["id"].startswith("sess-")
    assert body["alias"] == "neo"
    assert set(body) == {
        "id",
        "alias",
        "created_at",
        "token",
        "expires_at",
        "customer_name",
        "order_ids",
        "objectives",
    }
    assert "customer_id" not in body
    assert "route" not in body


def test_create_session_rejects_invalid_alias(client: TestClient) -> None:
    response = client.post("/api/sessions", json={"alias": "<script>", "accepted_rules": True})

    assert response.status_code == 422
