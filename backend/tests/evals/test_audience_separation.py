import pytest
from fastapi.testclient import TestClient

from agent_zero.evals.suite import evaluation_suite, fixture_hash, suite_hash
from tests.arena.support import join, send, wait_attempt
from tests.evals.support import OPERATOR, candidate, wait_evaluation

pytestmark = pytest.mark.requirement("CORE-07")


def test_audience_attempts_never_enter_the_frozen_evaluation_suite(
    evaluation_client: TestClient,
) -> None:
    client = evaluation_client
    frozen = [case.model_dump(mode="json") for case in evaluation_suite()]
    frozen_hash = suite_hash(evaluation_suite())
    frozen_fixtures = fixture_hash()
    frozen_messages = {message for case in frozen for message in case["messages"]}

    audience_messages = ["Zorro violeta quiere saber cuánto tarda el envío nacional."]
    attempt_ids = []
    for alias, message in zip(("neo", "trinity"), audience_messages * 2, strict=True):
        session = join(client, alias)
        attempt = send(client, session, message, key=f"sep-{alias}")
        wait_attempt(client, attempt["id"])
        attempt_ids.append(attempt["id"])
    audience = client.get("/api/operator/attempts", headers=OPERATOR).json()
    assert {row["id"] for row in audience} >= set(attempt_ids)
    assert all(row["origin"] != "evaluation" for row in audience)

    # The suite is rebuilt from code only: nothing the audience sent can reach it.
    assert [case.model_dump(mode="json") for case in evaluation_suite()] == frozen
    assert suite_hash(evaluation_suite()) == frozen_hash
    assert fixture_hash() == frozen_fixtures
    assert len(frozen) == 45
    assert not frozen_messages & set(audience_messages)

    version = candidate(client)
    response = client.post(
        "/api/operator/evaluations",
        headers=OPERATOR,
        json={
            "before_version": 0,
            "after_version": version,
            "repetitions": 1,
            "max_calls": 1200,
        },
    )
    assert response.status_code == 202, response.text
    result = wait_evaluation(client, response.json()["id"], timeout=200)
    assert result["status"] == "completed", result["stop_reason"]
    assert result["metadata"]["suite_hash"] == frozen_hash
    assert result["metadata"]["fixture_hash"] == frozen_fixtures
    assert result["report"]["planned"] == 90
    executions = result["results"]
    assert {row["case_id"] for row in executions} == {case["case_id"] for case in frozen}
    assert not {row["attempt_id"] for row in executions} & set(attempt_ids)
    assert not {row["attempt_id"] for row in executions} & {row["id"] for row in audience}
    for row in executions:
        assert "Zorro violeta" not in str(row)
