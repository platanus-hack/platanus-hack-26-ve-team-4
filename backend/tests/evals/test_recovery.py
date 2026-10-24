import asyncio
from copy import deepcopy
from typing import Any

import pytest
from fastapi.testclient import TestClient

from agent_zero.agent_gateway.business_policy import CallContext
from agent_zero.arena.core import ProductCore
from agent_zero.config import Settings
from agent_zero.evals.handler import EvaluationHandler
from agent_zero.evals.models import Evaluation, EvaluationExecution
from agent_zero.evals.suite import evaluation_suite
from agent_zero.main import create_app
from agent_zero.runtime.handlers import StepContext
from agent_zero.runtime.step_results import Advance, Complete
from agent_zero.runtime.tool_access import ToolAccess
from agent_zero.victim.arena_manifest import ARENA_VERSION
from tests.evals.support import OPERATOR, candidate, core_for, wait_evaluation


async def execute_step(core: ProductCore, evaluation_id: str) -> Advance | Complete:
    principal = await core.fleet.admission.admit("prober", ARENA_VERSION)
    result = await EvaluationHandler(core.fleet, core.evaluation_runner, core._llm).step(
        StepContext(
            run_id="manual-recovery-step",
            input={"evaluation_id": evaluation_id},
            checkpoint={},
            step_index=0,
            principal=principal,
            now=core.fleet.clock(),
        )
    )
    assert isinstance(result, Advance | Complete)
    return result


def test_restart_resumes_completed_grid_and_reexecutes_only_interrupted_case_in_clean_data(
    evaluation_settings: Settings,
) -> None:
    with TestClient(create_app(evaluation_settings)) as first:
        core = core_for(first)
        assert first.portal is not None
        first.portal.call(core.fleet.worker.stop)
        version = candidate(first)
        started = first.post(
            "/api/operator/evaluations",
            headers=OPERATOR,
            json={
                "after_version": version,
                "repetitions": 1,
            },
        )
        assert started.status_code == 202, started.text
        evaluation_id = started.json()["id"]
        assert isinstance(first.portal.call(execute_step, core, evaluation_id), Advance)
        assert isinstance(first.portal.call(execute_step, core, evaluation_id), Advance)
        initial = first.get(f"/api/operator/evaluations/{evaluation_id}", headers=OPERATOR).json()
        assert initial["completed"] == 2
        initial_attempts = [row["attempt_id"] for row in initial["results"]]

        async def interrupted() -> None:
            async with core.fleet.database.sessions() as db:
                db.add(
                    EvaluationExecution(
                        evaluation_id=evaluation_id,
                        ordinal=2,
                        status="running",
                        starts=1,
                        result={"uncommitted": True},
                    )
                )
                await db.commit()

        first.portal.call(interrupted)
    with TestClient(create_app(evaluation_settings)) as restored:
        result = wait_evaluation(restored, evaluation_id)
        assert result["status"] == "completed"
        assert result["completed"] == 90
        assert [row["attempt_id"] for row in result["results"][:2]] == initial_attempts
        assert result["results"][2]["interrupted_starts"] == 1
        assert result["report"]["interrupted_executions"] == 1
        assert len({row["attempt_id"] for row in result["results"]}) == 90
        assert result["report"]["calls"] >= 224


@pytest.mark.parametrize("target", ["cases", "policy"])
def test_recovery_rejects_tampered_suite_or_policy_before_calling_the_provider(
    evaluation_client: TestClient,
    target: str,
) -> None:
    client = evaluation_client
    core = core_for(client)
    assert client.portal is not None
    client.portal.call(core.fleet.worker.stop)
    version = candidate(client)
    started = client.post(
        "/api/operator/evaluations",
        headers=OPERATOR,
        json={
            "after_version": version,
            "repetitions": 1,
        },
    )
    assert started.status_code == 202
    evaluation_id = started.json()["id"]

    async def tamper() -> None:
        async with core.fleet.database.sessions() as db:
            evaluation = await db.get(Evaluation, evaluation_id)
            assert evaluation is not None
            if target == "cases":
                cases: list[dict[str, Any]] = deepcopy(evaluation.cases)
                cases[0]["messages"] = ["Una entrada sustituida durante la recuperación."]
                evaluation.cases = cases
            else:
                metadata = deepcopy(evaluation.metadata_json)
                metadata["policy_hashes"][str(version)] = "forged"
                evaluation.metadata_json = metadata
            await db.commit()

    client.portal.call(tamper)
    assert isinstance(client.portal.call(execute_step, core, evaluation_id), Complete)
    result = client.get(f"/api/operator/evaluations/{evaluation_id}", headers=OPERATOR).json()
    assert result["status"] == "stopped"
    assert result["stop_reason"] == (
        "suite_integrity_mismatch" if target == "cases" else "policy_integrity_mismatch"
    )
    assert result["completed"] == 0
    assert result["report"]["calls"] == 0
    assert result["report"]["pending"] == 90
    assert result["report"]["acceptance"]["zero_after_violations"] is False


def test_cancellation_after_real_refund_discards_isolated_state_and_releases_trace_capture(
    evaluation_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = evaluation_client
    core = core_for(client)
    assert client.portal is not None
    client.portal.call(core.fleet.worker.stop)
    candidate(client)
    case = next(case for case in evaluation_suite() if case.case_id == "legit-cust-ana-refund")
    original = core.executor.advance

    async def cancel_after_write(
        context: CallContext,
        tools: ToolAccess,
        state: dict[str, Any],
        messages: list[str],
    ) -> dict[str, Any]:
        result = await original(context, tools, state, messages)
        if state["phase"] == "execute":
            raise asyncio.CancelledError("Interrupted after a real isolated refund committed.")
        return result

    monkeypatch.setattr(core.executor, "advance", cancel_after_write)

    async def cancel_and_recover() -> None:
        with pytest.raises(asyncio.CancelledError):
            await core.evaluation_runner.run_case("cancelled-eval", 0, case, 1, 1200)
        assert core.observer._validation == {}
        assert set(core.environments._environments) == {"protected", "honeypot"}
        monkeypatch.setattr(core.executor, "advance", original)
        result = await core.evaluation_runner.run_case("cancelled-eval", 0, case, 1, 1200)
        assert result["utility_passed"] is True
        assert [row["amount_cents"] for row in result["state"]["refunds"]] == [500]
        assert core.observer._validation == {}

    client.portal.call(cancel_and_recover)
