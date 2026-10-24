import time

from fastapi.testclient import TestClient

from tests.evals.support import OPERATOR

ALLOWED_KEYS = {
    "version",
    "queries",
    "evaluable",
    "inconclusive",
    "pending",
    "violations",
    "success_rate",
    "ci_low",
    "ci_high",
    "queries_to_break",
    "censored",
    "first_break",
}


def test_public_endpoint_answers_without_credentials_when_there_is_no_campaign(
    evaluation_client: TestClient,
) -> None:
    response = evaluation_client.get("/api/arena/coevolution")

    assert response.status_code == 200
    assert response.json() == {
        "budget": 8,
        "evidence_mode": "simulated",
        "status": None,
        "versions": [],
        "summary": None,
    }


def test_public_curve_exposes_only_counters_mutator_and_family(
    evaluation_client: TestClient,
) -> None:
    started = evaluation_client.post(
        "/api/operator/campaigns",
        headers=OPERATOR,
        json={"max_attempts": 3, "generation": "adaptive"},
    )
    assert started.status_code == 202, started.text

    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        campaign = evaluation_client.get("/api/operator/campaigns", headers=OPERATOR).json()[0]
        if campaign["status"] != "running":
            break
        time.sleep(0.01)
    body = evaluation_client.get("/api/arena/coevolution")

    payload = body.json()
    assert payload["versions"]
    for row in payload["versions"]:
        assert set(row) == ALLOWED_KEYS
    text = body.text
    for case in campaign["cases"]:
        for message in case["case"]["messages"]:
            assert message not in text
    for forbidden in ("messages", "canary", "run_id", "attempt", "session", "campaign-", "AZP_"):
        assert forbidden not in text
