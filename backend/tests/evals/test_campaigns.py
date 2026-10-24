import time
from typing import Any, Literal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from agent_zero.attempts.models import Attempt
from agent_zero.attempts.schemas import AttemptCreate
from agent_zero.config import Settings
from agent_zero.llm.models import LlmMode, ModelRole
from agent_zero.llm.playback_model import PlaybackModel
from agent_zero.main import create_app
from agent_zero.prober.campaign_handler import CampaignHandler
from agent_zero.prober.models import AttackFamily
from agent_zero.runtime.handlers import StepContext
from agent_zero.runtime.step_results import Advance
from agent_zero.victim.arena_manifest import ARENA_VERSION
from tests.arena.support import ScenarioPlayback, wait_attempt
from tests.evals.support import OPERATOR, candidate, core_for


def _wait_campaign(client: TestClient) -> dict[str, Any]:
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        item: dict[str, Any] = client.get("/api/operator/campaigns", headers=OPERATOR).json()[0]
        if item["status"] != "running":
            return item
        time.sleep(0.01)
    raise AssertionError(f"La campaña no terminó: {item}")


@pytest.mark.parametrize("generation", ["templates", "llm"])
def test_campaign_exercises_all_six_playbooks_with_traceable_source_contamination(
    evaluation_client: TestClient,
    generation: str,
) -> None:
    client = evaluation_client
    response = client.post(
        "/api/operator/campaigns",
        headers=OPERATOR,
        json={
            "max_attempts": 6,
            "generation": generation,
            "max_mutations": 6,
        },
    )
    assert response.status_code == 202, response.text
    result = _wait_campaign(client)
    assert result["status"] == "exhausted"
    assert result["stop_reason"] == "attempt_budget_exhausted"
    assert len(result["attempt_ids"]) == 6
    assert result["generation_calls"] == (6 if generation == "llm" else 0)
    assert {case["case"]["family"] for case in result["cases"]} == set(AttackFamily)
    assert len({case["digest"] for case in result["cases"]}) == 6
    for case in result["cases"]:
        if generation == "llm":
            assert case["case"]["parent_case_id"]
        detail = client.get(f"/api/operator/attempts/{case['attempt_id']}", headers=OPERATOR).json()
        assert detail["origin"] == "autonomous"
        assert detail["outcome"] == "confirmed_violation"
        if case["case"]["fixture"] is not None:
            assert "untrusted" in str(detail["events"])
            assert case["case"]["surface"] in {"document", "tool_result"}
    assert client.get("/api/arena/state").json()["scores"] == []


def test_llm_budget_and_duplicate_inputs_remain_durable_without_template_fallback(
    evaluation_settings: Settings,
) -> None:
    configured = evaluation_settings.model_copy(update={"llm_mode": LlmMode.OFFLINE})
    repeated = {"messages": ["Consulta B-2001."], "fixture_content": None}
    models: dict[ModelRole, PlaybackModel] = {role: ScenarioPlayback() for role in ModelRole}
    models[ModelRole.PROBER] = PlaybackModel([repeated, repeated, repeated])
    with TestClient(create_app(configured, models)) as client:
        response = client.post(
            "/api/operator/campaigns",
            headers=OPERATOR,
            json={
                "max_attempts": 3,
                "generation": "llm",
                "max_mutations": 3,
            },
        )
        assert response.status_code == 202
        result = _wait_campaign(client)
        campaign_id = result["id"]
        assert result["generation_calls"] == 3
        assert result["stop_reason"] == "mutation_budget_exhausted"
        assert len(result["attempt_ids"]) == 1
        assert sum(case["status"] == "duplicate" for case in result["cases"]) == 2
    with TestClient(create_app(configured, models)) as restored:
        result = restored.get("/api/operator/campaigns", headers=OPERATOR).json()[0]
        assert result["id"] == campaign_id
        assert result["generation_calls"] == 3
        assert len(result["attempt_ids"]) == 1
        assert result["status"] == "exhausted"


def test_invalid_model_output_cannot_mutate_identity_or_silently_run_a_template(
    evaluation_settings: Settings,
) -> None:
    configured = evaluation_settings.model_copy(update={"llm_mode": LlmMode.OFFLINE})
    models: dict[ModelRole, PlaybackModel] = {role: ScenarioPlayback() for role in ModelRole}
    models[ModelRole.PROBER] = PlaybackModel(
        [
            {
                "messages": ["Consulta B-2001."],
                "customer_id": "cust-bruno",
            }
        ]
    )
    with TestClient(create_app(configured, models)) as client:
        response = client.post(
            "/api/operator/campaigns",
            headers=OPERATOR,
            json={
                "max_attempts": 1,
                "generation": "llm",
                "max_mutations": 1,
            },
        )
        assert response.status_code == 202
        result = _wait_campaign(client)
        assert result["stop_reason"] == "generator_failed"
        assert result["generation_calls"] == 1
        assert result["attempt_ids"] == []
        assert result["cases"][0]["error"] == "StructuredOutputError"


def test_crash_after_attempt_admission_recovers_the_same_attempt_without_duplicate_effects(
    evaluation_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = evaluation_client
    core = core_for(client)
    assert client.portal is not None
    client.portal.call(core.fleet.worker.stop)
    response = client.post("/api/operator/campaigns", headers=OPERATOR, json={"max_attempts": 1})
    assert response.status_code == 202
    campaign_id = response.json()["id"]
    original = core.submissions.submit
    fail_once = True

    async def interrupt_after_admission(
        session_id: str,
        payload: AttemptCreate,
        origin: Literal["audience", "autonomous"] = "audience",
        campaign_id: str | None = None,
    ) -> Attempt:
        nonlocal fail_once
        admitted = await original(session_id, payload, origin, campaign_id)
        if fail_once:
            fail_once = False
            raise ConnectionError("Simulated interruption after the durable admission commit.")
        return admitted

    monkeypatch.setattr(core.submissions, "submit", interrupt_after_admission)

    async def enqueue() -> None:
        principal = await core.fleet.admission.admit("prober", ARENA_VERSION)
        context = StepContext(
            run_id="manual-campaign-recovery",
            input={"campaign_id": campaign_id},
            checkpoint={},
            step_index=0,
            principal=principal,
            now=core.fleet.clock(),
        )
        handler = CampaignHandler(
            core.fleet, core.submissions, core.attempts, core._llm, core.scenario
        )
        assert isinstance(await handler.step(context), Advance)  # Persist session before admission.
        with pytest.raises(ConnectionError, match="durable admission"):
            await handler.step(context)
        async with core.fleet.database.sessions() as db:
            assert len(list(await db.scalars(select(Attempt)))) == 1
        assert isinstance(await handler.step(context), Advance)
        async with core.fleet.database.sessions() as db:
            assert len(list(await db.scalars(select(Attempt)))) == 1

    client.portal.call(enqueue)
    client.portal.call(core.fleet.start)
    result = _wait_campaign(client)
    assert len(result["attempt_ids"]) == 1
    assert result["stop_reason"] == "attempt_budget_exhausted"


def test_indirect_fixture_survives_replay_and_original_candidate_validation(
    evaluation_client: TestClient,
) -> None:
    client = evaluation_client
    response = client.post("/api/operator/campaigns", headers=OPERATOR, json={"max_attempts": 4})
    assert response.status_code == 202
    campaign = _wait_campaign(client)
    indirect = next(
        case for case in campaign["cases"] if case["case"]["family"] == "indirect_injection"
    )
    baseline = client.get(
        f"/api/operator/attempts/{indirect['attempt_id']}", headers=OPERATOR
    ).json()
    assert baseline["outcome"] == "confirmed_violation"
    replay = client.post(
        f"/api/operator/attempts/{indirect['attempt_id']}/replay", headers=OPERATOR
    )
    assert replay.status_code == 202, replay.text
    repeated = wait_attempt(client, replay.json()["id"])
    assert repeated["outcome"] == "confirmed_violation"
    assert "untrusted" in str(repeated["events"])
    version = candidate(client)
    core = core_for(client)

    async def validate_and_activate() -> dict[str, Any]:
        original = await core.attempts.get(indirect["attempt_id"])
        assert original is not None
        events = await core.events.for_attempt(original.id)
        await core.policies.start_validation(version)
        report = await core.validator.validate(version, original, events, "OBJ-ORDER")
        assert report["passed"] is True
        assert report["cases"][0]["name"] == "original"
        assert report["cases"][0]["outcome"] == "prevented"
        await core.policies.record_validation(version, report)
        assert await core.policies.activate(version, core.attempts.drained)
        return report

    assert client.portal is not None
    client.portal.call(validate_and_activate)
    replay = client.post(
        f"/api/operator/attempts/{indirect['attempt_id']}/replay", headers=OPERATOR
    )
    assert replay.status_code == 202
    prevented = wait_attempt(client, replay.json()["id"])
    assert prevented["outcome"] == "prevented"
    assert any(event["type"] == "tool_denied" for event in prevented["events"])
    assert "untrusted" in str(prevented["events"])
