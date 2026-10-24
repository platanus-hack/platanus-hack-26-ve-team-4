import time
from datetime import UTC, datetime, timedelta
from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent_zero.arena.core import ProductCore
from agent_zero.config import Settings
from agent_zero.main import create_app
from agent_zero.sessions.session_token import InvalidSessionTokenError, SessionTokens
from tests.arena.support import OPERATOR, foreign_order, join, send, wait_attempt

pytestmark = pytest.mark.requirement("CORE-07")


def test_tokens_detect_expiry_and_tampering(settings: Settings) -> None:
    codec = SessionTokens(settings)
    now = datetime.now(UTC)
    token = codec.issue("sess-one", now + timedelta(seconds=60))
    assert codec.verify(token, now) == "sess-one"
    with pytest.raises(InvalidSessionTokenError):
        codec.verify(token + "bad", now)
    with pytest.raises(InvalidSessionTokenError):
        codec.verify(token, now + timedelta(seconds=61))


def test_unique_identities_ownership_and_pause(manual_client: TestClient) -> None:
    first, second, third = (join(manual_client, alias) for alias in ("neo", "trinity", "morpheus"))
    assert len({session["customer_name"] for session in (first, second, third)}) == 3
    assert (
        manual_client.post(
            "/api/sessions", json={"alias": "cuarto", "accepted_rules": True}
        ).status_code
        == 409
    )
    attempt = send(manual_client, first, "¿Cuánto tarda el envío?")
    assert (
        manual_client.get(
            f"/api/attempts/{attempt['id']}", headers={"Authorization": f"Bearer {second['token']}"}
        ).status_code
        == 404
    )
    wait_attempt(manual_client, attempt["id"])
    manual_client.post("/api/operator/arena/pause", headers=OPERATOR)
    assert (
        manual_client.post(
            "/api/attempts",
            headers={"Authorization": f"Bearer {first['token']}"},
            json={"message": "Hola", "idempotency_key": "closed"},
        ).status_code
        == 409
    )


def test_prober_exhausts_its_budget_and_never_competes_with_audience(
    manual_client: TestClient,
) -> None:
    response = manual_client.post(
        "/api/operator/campaigns", headers=OPERATOR, json={"max_attempts": 3}
    )
    assert response.status_code == 202, response.text
    for _ in range(700):
        campaign = manual_client.get("/api/operator/campaigns", headers=OPERATOR).json()[0]
        if campaign["status"] == "exhausted":
            break
        time.sleep(0.01)
    assert campaign["status"] == "exhausted", campaign
    assert len(campaign["attempt_ids"]) == 3
    attempts = manual_client.get("/api/operator/attempts", headers=OPERATOR).json()
    assert all(attempt["origin"] == "autonomous" for attempt in attempts)
    assert manual_client.get("/api/arena/state").json()["scores"] == []
    findings = manual_client.get("/api/operator/findings", headers=OPERATOR).json()
    assert {finding["objective_id"] for finding in findings} == {
        "OBJ-ORDER",
        "OBJ-REFUND",
        "OBJ-MEMORY",
    }


def test_failed_provider_is_inconclusive(settings: Settings) -> None:
    configured = settings.model_copy(update={"runtime_poll_seconds": 0.005})
    with TestClient(create_app(configured)) as client:
        session = join(client)
        result = wait_attempt(client, send(client, session, "Consulta A-1001.")["id"])
        assert result["outcome"] == "inconclusive"
        assert client.get("/api/operator/findings", headers=OPERATOR).json() == []


def test_an_enqueued_attempt_keeps_its_policy_and_activation_waits_for_drain(
    manual_client: TestClient,
) -> None:
    session = join(manual_client)
    core: ProductCore = cast(FastAPI, manual_client.app).state.core
    assert manual_client.portal is not None
    manual_client.portal.call(core.fleet.worker.stop)
    attempt = send(manual_client, session, f"Consulta {foreign_order(session)}.")
    assert attempt["policy_version"] == 0

    async def attempt_activation() -> bool:
        version = await core.policies.propose("finding-test", "OBJ-ORDER")
        assert version is not None
        await core.policies.start_validation(version)
        await core.policies.record_validation(version, {"passed": True})
        return await core.policies.activate(version, core.attempts.drained)

    assert manual_client.portal.call(attempt_activation) is False
    assert manual_client.get("/api/arena/state").json()["policy_version"] == 0
    # The policy snapshot is immutable even if admission resumes later.
    observed = manual_client.get(f"/api/operator/attempts/{attempt['id']}", headers=OPERATOR).json()
    assert observed["policy_version"] == 0
