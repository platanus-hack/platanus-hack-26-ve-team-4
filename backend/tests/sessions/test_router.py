from fastapi.testclient import TestClient

from agent_zero.victim.fixtures import customer_ids, orders_for_customer


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


def test_session_identity_matches_the_name_on_its_orders(client: TestClient) -> None:
    body = client.post("/api/sessions", json={"alias": "neo", "accepted_rules": True}).json()
    names = {
        order.order_id: order.customer_name
        for customer in customer_ids(500)
        for order in orders_for_customer(customer)
    }

    assert {names[order_id] for order_id in body["order_ids"]} == {body["customer_name"]}
    me = client.get("/api/sessions/me", headers={"Authorization": f"Bearer {body['token']}"})
    assert me.json()["customer_name"] == body["customer_name"]


def test_create_session_rejects_invalid_alias(client: TestClient) -> None:
    response = client.post("/api/sessions", json={"alias": "<script>", "accepted_rules": True})

    assert response.status_code == 422
