from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from agent_zero.attempts.models import Attempt, AttemptOutcome, AttemptStatus
from agent_zero.evals.round_curve import coevolution
from agent_zero.prober.campaign_models import Campaign, CampaignCaseRecord, CampaignPlan
from agent_zero.prober.playbooks import campaign_case
from agent_zero.routing.models import Route
from tests.evals.support import core_for

START = datetime(2026, 10, 24, 12, tzinfo=UTC)
V = AttemptOutcome.CONFIRMED_VIOLATION
P = AttemptOutcome.PREVENTED
INC = AttemptOutcome.INCONCLUSIVE


def _seed(client: TestClient, plan: list[tuple[int, AttemptOutcome | None, str, str]]) -> None:
    async def write() -> None:
        core = core_for(client)
        async with core.fleet.database.sessions() as db:
            db.add(
                Campaign(
                    id="camp-seed",
                    status="exhausted",
                    max_attempts=60,
                    attempt_ids=[],
                    case_hashes=[],
                    created_at=START,
                )
            )
            db.add(
                CampaignPlan(
                    campaign_id="camp-seed",
                    generation="adaptive",
                    max_mutations=0,
                    generation_calls=0,
                    stop_reason="",
                )
            )
            for index, (version, outcome, origin, mutator) in enumerate(plan):
                customer, case, digest = campaign_case(index % 6, "camp-seed")
                case = case.model_copy(update={"mutator": None if mutator == "seed" else mutator})
                stamp = START + timedelta(seconds=index)
                db.add(
                    Attempt(
                        id=f"attempt-{index}",
                        session_id="sess-x",
                        origin=origin,
                        campaign_id="camp-seed",
                        policy_version=version,
                        route=Route.PROTECTED,
                        run_id=f"run-{index}",
                        idempotency_key=f"k-{index}",
                        messages=case.messages,
                        customer_id=customer,
                        objective_id=case.objective_id,
                        status=AttemptStatus.EVALUATED,
                        outcome=outcome,
                        assessment={},
                        created_at=stamp,
                        updated_at=stamp,
                    )
                )
                db.add(
                    CampaignCaseRecord(
                        campaign_id="camp-seed",
                        index=index,
                        status="submitted",
                        customer_id=customer,
                        case_json=case.model_dump(mode="json"),
                        digest=f"{digest}-{index}",
                        session_id="sess-x",
                        attempt_id=f"attempt-{index}",
                        error="",
                    )
                )
            await db.commit()

    assert client.portal is not None
    client.portal.call(write)


def _curve(client: TestClient) -> dict[str, Any]:
    core = core_for(client)

    async def read() -> dict[str, Any]:
        async with core.fleet.database.sessions() as db:
            return await coevolution(db, core.fleet.settings)

    assert client.portal is not None
    return client.portal.call(read)


def test_curve_groups_by_version_with_denominator_wilson_and_censoring(
    evaluation_client: TestClient,
) -> None:
    _seed(
        evaluation_client,
        [
            (0, P, "autonomous", "seed"),
            (0, P, "autonomous", "chain"),
            (0, V, "autonomous", "paraphrase_es"),
            (0, V, "autonomous", "seed"),
            (1, P, "autonomous", "seed"),
            (1, INC, "autonomous", "chain"),
            (1, None, "autonomous", "seed"),
            (1, P, "autonomous", "split_turns"),
            (2, P, "audience", "seed"),
        ],
    )

    curve = _curve(evaluation_client)

    first, second = curve["versions"]
    assert [row["version"] for row in curve["versions"]] == [0, 1]
    assert (first["queries"], first["evaluable"], first["violations"]) == (4, 4, 2)
    assert first["success_rate"] == 0.5
    assert first["ci_low"] == pytest.approx(0.15, abs=0.01)
    assert first["ci_high"] == pytest.approx(0.85, abs=0.01)
    assert first["queries_to_break"] == 3
    assert first["censored"] is False
    assert first["first_break"] == {"mutator": "paraphrase_es", "family": "memory_poisoning"}
    assert (second["queries"], second["inconclusive"], second["pending"]) == (4, 1, 1)
    assert second["evaluable"] == 2
    assert second["violations"] == 0
    assert second["censored"] is True
    assert second["queries_to_break"] is None
    assert second["ci_low"] == 0.0
    assert curve["summary"]["baseline"]["version"] == 0
    assert curve["summary"]["latest"]["version"] == 1
    assert curve["budget"] == 8


def test_audience_attempts_never_enter_the_curve(evaluation_client: TestClient) -> None:
    _seed(evaluation_client, [(0, V, "audience", "seed")])

    curve = _curve(evaluation_client)

    assert curve["versions"] == []
    assert curve["summary"] is None


def test_without_an_adaptive_campaign_the_curve_is_empty(evaluation_client: TestClient) -> None:
    curve = _curve(evaluation_client)

    assert curve["versions"] == []
    assert curve["status"] is None
    assert curve["evidence_mode"] == "simulated"
