from fastapi.testclient import TestClient

from agent_zero.config import Settings
from agent_zero.llm.models import LlmMode
from agent_zero.main import create_app
from tests.evals.support import OPERATOR, candidate, wait_evaluation


def test_unavailable_provider_stops_with_inconclusives_and_no_fabricated_defensive_win(
    evaluation_settings: Settings,
) -> None:
    configured = evaluation_settings.model_copy(update={"llm_mode": LlmMode.OFFLINE})
    with TestClient(create_app(configured)) as client:
        version = candidate(client)
        response = client.post(
            "/api/operator/evaluations",
            headers=OPERATOR,
            json={
                "before_version": 0,
                "after_version": version,
                "repetitions": 1,
            },
        )
        assert response.status_code == 202, response.text
        result = wait_evaluation(client, response.json()["id"])
        report = result["report"]
        assert result["status"] == "stopped"
        assert result["stop_reason"] == "consecutive_infrastructure_failures"
        assert report["completed"] == 3
        assert report["pending"] == 87
        assert report["comparison_complete"] is False
        assert report["acceptance"]["zero_after_violations"] is False
        assert report["violation_reduction_percentage_points"] is None
        for metrics in report["versions"].values():
            assert metrics["adversarial"]["evaluable"] == 0
            assert metrics["adversarial"]["confirmed_violations"] == 0
            assert metrics["adversarial"]["violation_rate"] is None
            assert metrics["adversarial"]["conservative_rate"] == 1
        assert all(row["error"] == "PlaybackExhaustedError" for row in result["results"])
