import time

from fastapi.testclient import TestClient

from agent_zero.config import Settings
from agent_zero.main import create_app
from tests.evals.support import OPERATOR

BUDGET = 3


def _curve(client: TestClient) -> list[dict[str, int]]:
    versions: list[dict[str, int]] = client.get("/api/arena/coevolution").json()["versions"]
    return versions


def test_restart_during_a_held_round_neither_duplicates_admissions_nor_resets_the_budget(
    evaluation_settings: Settings,
) -> None:
    configured = evaluation_settings.model_copy(
        update={"arena_auto_patch": False, "prober_round_query_budget": BUDGET}
    )
    with TestClient(create_app(configured)) as client:
        response = client.post(
            "/api/operator/campaigns",
            headers=OPERATOR,
            json={"max_attempts": 30, "generation": "adaptive"},
        )
        assert response.status_code == 202
        campaign_id = response.json()["id"]
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            rows = _curve(client)
            if rows and rows[0]["queries"] == BUDGET and rows[0]["pending"] == 0:
                break
            time.sleep(0.01)
        else:
            raise AssertionError("La ronda 0 no se llenó.")
        before = client.get("/api/operator/campaigns", headers=OPERATOR).json()[0]["attempt_ids"]
    with TestClient(create_app(configured)) as restored:
        time.sleep(0.5)
        campaign = restored.get("/api/operator/campaigns", headers=OPERATOR).json()[0]
        assert campaign["id"] == campaign_id
        assert campaign["status"] == "running"
        assert campaign["attempt_ids"] == before
        assert len(before) == BUDGET
        assert _curve(restored)[0]["queries"] == BUDGET
