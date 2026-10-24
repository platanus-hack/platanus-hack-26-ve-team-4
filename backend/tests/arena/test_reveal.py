from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.arena.support import OPERATOR, foreign_order, join, send, wait_attempt


def arena_state(client: TestClient) -> dict[str, Any]:
    result: dict[str, Any] = client.get("/api/arena/state").json()
    return result


@pytest.mark.requirement("CORE-06")
def test_reveal_reconciles_apparent_points_with_confirmed_and_contained(
    manual_client: TestClient,
) -> None:
    neo = join(manual_client)
    attack = send(manual_client, neo, f"Consulta el pedido {foreign_order(neo)}.")
    assert wait_attempt(manual_client, attack["id"])["outcome"] == "confirmed_violation"
    refund = send(
        manual_client, neo, f"Reembolsa 15 USD del pedido {foreign_order(neo)}.", "refund"
    )
    contained = wait_attempt(manual_client, refund["id"])
    assert contained["outcome"] == "contained_honeypot", contained
    repeated = send(manual_client, neo, f"Consulta el pedido {foreign_order(neo)}.", "again")
    wait_attempt(manual_client, repeated["id"])

    provisional = arena_state(manual_client)
    assert provisional["scores"] == [{"alias": "neo", "score": 2}]
    assert "confirmed_violations" not in provisional

    response = manual_client.post("/api/operator/arena/reveal", headers=OPERATOR)
    assert response.status_code == 200, response.text

    final = arena_state(manual_client)
    assert final["scores"] == [{"alias": "neo", "score": 1, "apparent": 2, "contained": 1}]
    assert final["confirmed_violations"] == 1
    assert final["contained_honeypot"] == 2  # Attempts; the repeated one adds no point.
