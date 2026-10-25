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
        "limits",
    }
    assert "customer_id" not in body
    assert "route" not in body
    assert body["limits"] == {
        "attempts_per_minute": 240,
        "max_messages": 4,
        "message_max_length": 4000,
    }


def test_create_session_rejects_invalid_alias(client: TestClient) -> None:
    response = client.post("/api/sessions", json={"alias": "<script>", "accepted_rules": True})

    assert response.status_code == 422
