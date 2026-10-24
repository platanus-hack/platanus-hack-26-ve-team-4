from typing import Any, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent_zero.arena.core import ProductCore
from tests.arena.support import OPERATOR, join, send, wait_attempt

pytestmark = pytest.mark.requirement("CORE-05")


def evidence(client: TestClient, attempt_id: str) -> dict[str, Any]:
    response = client.get(f"/api/operator/attempts/{attempt_id}", headers=OPERATOR)
    assert response.status_code == 200, response.text
    result: dict[str, Any] = response.json()
    return result


def test_pausing_lets_an_accepted_attempt_finish_keeps_its_events_and_closes_admission(
    manual_client: TestClient,
) -> None:
    core: ProductCore = cast(FastAPI, manual_client.app).state.core
    portal = manual_client.portal
    assert portal is not None
    session, other = join(manual_client, "neo"), join(manual_client, "trinity")
    portal.call(core.fleet.worker.stop)
    attempt = send(manual_client, session, f"Consulta el pedido {session['order_ids'][0]}.")
    # One worker step: the attempt is accepted and executing when the operator pauses.
    assert portal.call(core.fleet.worker.run_once) == 1
    in_flight = evidence(manual_client, attempt["id"])
    assert in_flight["status"] == "running", in_flight
    recorded = in_flight["events"]
    assert {"attempt_queued", "attempt_started"} <= {event["type"] for event in recorded}

    paused = manual_client.post("/api/operator/arena/pause", headers=OPERATOR)
    assert paused.status_code == 200, paused.text
    assert paused.json()["accepting"] is False
    headers = {"Authorization": f"Bearer {session['token']}"}
    # `other` has nothing pending, so only the pause can reject its attempt.
    for owner, key in ((other, "closed-other"), (session, "closed")):
        closed = manual_client.post(
            "/api/attempts",
            headers={"Authorization": f"Bearer {owner['token']}"},
            json={"message": "Hola", "idempotency_key": key},
        )
        assert closed.status_code == 409, closed.text
        assert closed.json()["detail"] == "Las entradas de la ronda están cerradas."

    async def resume_worker() -> None:
        core.fleet.worker.start()

    portal.call(resume_worker)
    finished = wait_attempt(manual_client, attempt["id"])
    assert finished["status"] == "evaluated", finished
    assert finished["outcome"] == "not_achieved", finished
    after = finished["events"]
    assert after[: len(recorded)] == recorded
    assert "attempt_evaluated" in {event["type"] for event in after}

    assert manual_client.get("/api/arena/state").json()["accepting"] is False
    late = manual_client.post(
        "/api/attempts", headers=headers, json={"message": "Hola", "idempotency_key": "late"}
    )
    assert late.status_code == 409, late.text
    attempts = manual_client.get("/api/operator/attempts", headers=OPERATOR).json()
    assert [row["id"] for row in attempts] == [attempt["id"]]
