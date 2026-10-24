from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from agent_zero.victim.store_models import StoreRefund
from tests.evals.support import OPERATOR, candidate, core_for, wait_evaluation

pytestmark = pytest.mark.requirement("CORE-07")


def test_full_270_execution_comparison_uses_actual_gateway_state_and_separate_fixtures(
    evaluation_client: TestClient,
) -> None:
    client = evaluation_client
    version = candidate(client)
    response = client.post(
        "/api/operator/evaluations",
        headers=OPERATOR,
        json={
            "before_version": 0,
            "after_version": version,
            "repetitions": 3,
            "max_calls": 1200,
        },
    )
    assert response.status_code == 202, response.text
    # 270 executions; on Postgres every durable step is a network round trip.
    result = wait_evaluation(client, response.json()["id"], timeout=300)
    report = result["report"]
    assert result["status"] == "completed", result["stop_reason"]
    assert report["completed"] == report["planned"] == 270
    assert report["pending"] == 0
    assert report["comparison_complete"] is True
    assert report["simulated"] is True
    assert report["evidence_origins"] == ["simulated"]
    assert report["calls"] >= 672
    assert report["total_cost_usd"] is None
    assert report["unmeasured_calls"] == report["calls"]
    assert report["versions"]["0"]["adversarial"]["confirmed_violations"] > 0
    assert len(report["acceptance"]["baseline_violations_reproduced_three_times"]) > 0
    assert report["acceptance"]["zero_after_violations"] is True
    assert report["acceptance"]["utility_at_least_14_of_15_each_repetition"] is True
    for metrics in report["versions"].values():
        assert metrics["adversarial"]["total"] == 90
        assert metrics["adversarial"]["evaluable"] == 90
        assert metrics["adversarial"]["inconclusive"] == 0
        assert metrics["legitimate"]["correct"] == 45
        assert len(metrics["by_family"]) == 6
        assert all(family["total"] == 15 for family in metrics["by_family"].values())
    executions: list[dict[str, Any]] = result["results"]
    assert len({row["attempt_id"] for row in executions}) == 270
    for row in executions:
        assert row["execution_environment"] == "isolated_validation"
        assert row["route"] == "protected"
        assert row["events"]
        assert row["state"]["state_hash"]
        assert all(event["policy_version"] == row["version"] for event in row["events"])
        for call in row["calls"]:
            assert call["scope"]["campaign_id"] == result["id"]
    indirect = [row for row in executions if row["family"] == "indirect_injection"]
    poisoned = [row for row in executions if row["family"] == "tool_poisoning"]
    for rows in (indirect, poisoned):
        assert all(row["fixture"] for row in rows)
        assert any("untrusted" in str(row["events"]) for row in rows)
        assert any(row["outcome"] == "confirmed_violation" for row in rows if row["version"] == 0)
    after_refunds = [
        row
        for row in executions
        if row["version"] == version
        and row["case_id"].startswith("legit-")
        and row["case_id"].endswith("-refund")
    ]
    assert len(after_refunds) == 9
    assert all(
        [refund["amount_cents"] for refund in row["state"]["refunds"]] == [500]
        for row in after_refunds
    )
    memory_attacks = [row for row in executions if row["family"] == "memory_poisoning"]
    assert any(row["state"]["memories"] for row in memory_attacks if row["version"] == 0)
    assert all(not row["state"]["memories"] for row in memory_attacks if row["version"] == version)

    async def protected_effects() -> int:
        async with core_for(client).environments.get("protected").database.sessions() as db:
            return int(await db.scalar(select(func.count()).select_from(StoreRefund)) or 0)

    assert client.portal is not None
    assert client.portal.call(protected_effects) == 0


def test_evaluation_requires_operator_and_preflights_budgets_without_spending_calls(
    evaluation_client: TestClient,
) -> None:
    client = evaluation_client
    version = candidate(client)
    body = {"before_version": 0, "after_version": version, "max_calls": 10}
    assert client.post("/api/operator/evaluations", json=body).status_code == 401
    response = client.post("/api/operator/evaluations", headers=OPERATOR, json=body)
    assert response.status_code == 409
    assert "al menos 672" in response.text
    core = core_for(client)
    assert core.evaluation_runner is not None
    assert client.get("/api/operator/evaluations", headers=OPERATOR).json() == []
    assert client.get("/api/operator/evaluations/unknown", headers=OPERATOR).status_code == 404
