import time
from typing import Any, cast

from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent_zero.arena.core import ProductCore

OPERATOR = {"X-Operator-Secret": "change-me"}


def core_for(client: TestClient) -> ProductCore:
    return cast(ProductCore, cast(FastAPI, client.app).state.core)


def candidate(client: TestClient) -> int:
    async def prepare() -> int:
        core = core_for(client)
        await core.ensure_agents()
        version = await core.policies.propose(
            "eval-order",
            "OBJ-ORDER",
            related=[("eval-refund", "OBJ-REFUND"), ("eval-memory", "OBJ-MEMORY")],
        )
        assert version is not None
        return version

    assert client.portal is not None
    return client.portal.call(prepare)


def wait_evaluation(client: TestClient, evaluation_id: str, timeout: float = 100) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get("/api/operator/evaluations", headers=OPERATOR)
        assert response.status_code == 200, response.text
        item = next(row for row in response.json() if row["id"] == evaluation_id)
        if item["status"] != "running" and item["report"]:
            result: dict[str, Any] = client.get(
                f"/api/operator/evaluations/{evaluation_id}",
                headers=OPERATOR,
            ).json()
            return result
        time.sleep(0.02)
    raise AssertionError(f"La evaluación no terminó: {item}")
