import asyncio
import time
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from agent_zero.attempts.models import Attempt
from agent_zero.config import Settings
from agent_zero.events.models import EventType
from agent_zero.events.public_projection import PUBLIC_FIELDS
from agent_zero.main import create_app
from agent_zero.prober.adaptive_candidates import OBJECTIVES, SEED_ARM, candidate
from agent_zero.prober.campaign_models import CampaignCaseRecord
from tests.evals.support import OPERATOR, core_for

BUDGET = 4


@pytest.fixture
def manual_adaptive_client(evaluation_settings: Settings) -> Iterator[TestClient]:
    configured = evaluation_settings.model_copy(
        update={"arena_auto_patch": False, "prober_round_query_budget": BUDGET}
    )
    with TestClient(create_app(configured)) as client:
        yield client


@pytest.fixture
def automatic_adaptive_client(evaluation_settings: Settings) -> Iterator[TestClient]:
    configured = evaluation_settings.model_copy(update={"arena_auto_patch": True})
    with TestClient(create_app(configured)) as client:
        yield client


def _campaign(client: TestClient) -> dict[str, Any]:
    item: dict[str, Any] = client.get("/api/operator/campaigns", headers=OPERATOR).json()[0]
    return item


def _wait(client: TestClient, done: Any, timeout: float = 90) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if done(client):
            return _campaign(client)
        time.sleep(0.01)
    raise AssertionError(f"Condición no alcanzada: {_campaign(client)}")


def _curve(client: TestClient) -> dict[str, Any]:
    body: dict[str, Any] = client.get("/api/arena/coevolution").json()
    return body


def _round_is_full(client: TestClient) -> bool:
    versions = _curve(client)["versions"]
    return bool(versions) and versions[-1]["queries"] == BUDGET and versions[-1]["pending"] == 0


def _activate_patch_for_a_break(client: TestClient, campaign: dict[str, Any]) -> int:
    core = core_for(client)
    broken = next(
        case
        for case in campaign["cases"]
        if client.get(f"/api/operator/attempts/{case['attempt_id']}", headers=OPERATOR).json()[
            "outcome"
        ]
        == "confirmed_violation"
    )
    objective = broken["case"]["objective_id"]
    others = [(f"eval-{other}", other) for other in OBJECTIVES if other != objective]

    async def patch() -> int:
        version = await core.policies.propose(f"eval-{objective}", objective, related=others)
        assert version is not None
        original = await core.attempts.get(broken["attempt_id"])
        assert original is not None
        events = await core.events.for_attempt(original.id)
        await core.policies.start_validation(version)
        report = await core.validator.validate(version, original, events, objective)
        assert report["passed"] is True
        await core.policies.record_validation(version, report)
        # El DefenseScheduler puede activar la candidata validada antes que la prueba,
        # o la cola puede no estar drenada todavía: se espera a que la versión quede activa.
        deadline = time.monotonic() + 30
        while not await core.policies.activate(version, core.attempts.drained):
            assert time.monotonic() < deadline, "la versión validada no llegó a activarse"
            await asyncio.sleep(0.05)
        assert await core.policies.active_version() == version
        return version

    assert client.portal is not None
    return client.portal.call(patch)


def _replayed_digests(client: TestClient, campaign: dict[str, Any]) -> list[str]:
    core = core_for(client)

    async def replay() -> list[str]:
        async with core.fleet.database.sessions() as db:
            rows = list(
                await db.scalars(
                    select(CampaignCaseRecord)
                    .where(CampaignCaseRecord.campaign_id == campaign["id"])
                    .order_by(CampaignCaseRecord.index)
                )
            )
            versions = {
                attempt.id: attempt.policy_version for attempt in await db.scalars(select(Attempt))
            }
        seen: set[str] = set()
        digests = []
        for row in rows:
            arm = (row.case_json["objective_id"], row.case_json.get("mutator") or SEED_ARM)
            again = candidate(arm, campaign["id"], row.index, versions[row.attempt_id or ""], seen)
            assert again is not None
            digests.append(again.digest)
            seen.add(row.digest)
        return digests

    assert client.portal is not None
    return client.portal.call(replay)


def test_adaptive_campaign_breaks_v0_then_holds_after_a_patch_with_exact_counts(
    manual_adaptive_client: TestClient,
) -> None:
    client = manual_adaptive_client
    response = client.post(
        "/api/operator/campaigns",
        headers=OPERATOR,
        json={"max_attempts": 40, "generation": "adaptive"},
    )
    assert response.status_code == 202, response.text
    assert (
        client.post(
            "/api/operator/campaigns",
            headers=OPERATOR,
            json={"max_attempts": 2, "generation": "adaptive"},
        ).status_code
        == 409
    )

    paused = _wait(client, _round_is_full)
    assert paused["status"] == "running"
    before = _curve(client)["versions"]
    assert [row["version"] for row in before] == [0]
    assert before[0]["queries"] == BUDGET
    assert before[0]["violations"] >= 1
    assert before[0]["censored"] is False
    time.sleep(0.3)
    assert len(_campaign(client)["attempt_ids"]) == BUDGET

    assert _activate_patch_for_a_break(client, paused) == 1

    finished = _wait(client, lambda c: _campaign(c)["status"] != "running")
    assert finished["stop_reason"] == "held_within_budget"
    curve = _curve(client)
    rows = curve["versions"]
    assert [row["version"] for row in rows] == [0, 1]
    assert [row["queries"] for row in rows] == [BUDGET, BUDGET]
    assert rows[0]["success_rate"] > rows[1]["success_rate"] == 0.0
    assert rows[1]["violations"] == 0
    assert rows[1]["censored"] is True
    assert rows[1]["evaluable"] == BUDGET
    assert rows[1]["inconclusive"] == 0
    assert curve["summary"]["baseline"]["queries_to_break"] == rows[0]["queries_to_break"]
    assert curve["summary"]["latest"]["queries_to_break"] is None
    assert len(finished["attempt_ids"]) == 2 * BUDGET
    assert all(
        client.get(f"/api/operator/attempts/{case['attempt_id']}", headers=OPERATOR).json()[
            "origin"
        ]
        == "autonomous"
        for case in finished["cases"]
    )
    assert client.get("/api/arena/state").json()["scores"] == []


def test_the_same_campaign_seed_regenerates_the_same_cases(
    manual_adaptive_client: TestClient,
) -> None:
    client = manual_adaptive_client
    client.post(
        "/api/operator/campaigns",
        headers=OPERATOR,
        json={"max_attempts": BUDGET, "generation": "adaptive"},
    )
    finished = _wait(client, lambda c: _campaign(c)["status"] != "running")

    assert _replayed_digests(client, finished) == [case["digest"] for case in finished["cases"]]


def test_closed_rounds_are_announced_publicly_with_counters_only(
    automatic_adaptive_client: TestClient,
) -> None:
    client = automatic_adaptive_client
    client.post(
        "/api/operator/campaigns",
        headers=OPERATOR,
        json={"max_attempts": 40, "generation": "adaptive"},
    )
    finished = _wait(client, lambda c: _campaign(c)["status"] != "running", timeout=120)
    core = core_for(client)
    assert client.portal is not None
    events = client.portal.call(core.events.public_after, 0)
    closed = [event for event in events if event.type is EventType.PROBE_ROUND_CLOSED]

    versions = [event.data["probe_round"] for event in closed]
    assert versions == sorted(set(versions))
    assert finished["stop_reason"] == "held_within_budget"
    for event in closed:
        assert event.attempt_id is None
        assert event.session_id is None
        assert set(event.data) <= PUBLIC_FIELDS
        assert event.data["queries"] >= 1
        assert event.policy_version == event.data["probe_round"]
    curve = _curve(client)["versions"]
    assert {row["version"]: row["queries"] for row in curve} == {
        event.data["probe_round"]: event.data["queries"] for event in closed
    }
    assert curve[0]["violations"] >= 1
    assert curve[-1]["violations"] == 0
    assert curve[-1]["queries"] == core.fleet.settings.prober_round_query_budget
