from datetime import timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.arena.round_models import RoundArchive
from agent_zero.arena.transactions import serialize_write
from agent_zero.evals.models import Evaluation, EvaluationExecution
from agent_zero.evals.reporting import build_report
from agent_zero.evals.runner import EvaluationRunner
from agent_zero.evals.schemas import EvaluationCase
from agent_zero.evals.service import EVALUATION_HANDLER
from agent_zero.evals.suite import canonical_hash, fixture_hash
from agent_zero.fleet.fleet_builder import Fleet
from agent_zero.llm.gateway import LlmGateway
from agent_zero.llm.schemas import CallRecord
from agent_zero.policies.repository import PolicyRepository
from agent_zero.runtime.handlers import StepContext
from agent_zero.runtime.step_results import Advance, Complete, Fail, StepResult, Wait


class EvaluationHandler:
    name = EVALUATION_HANDLER

    def __init__(self, fleet: Fleet, runner: EvaluationRunner, llm: LlmGateway) -> None:
        self._fleet = fleet
        self._runner = runner
        self._llm = llm

    async def step(self, context: StepContext) -> StepResult:
        evaluation_id = str(context.input["evaluation_id"])
        async with self._fleet.database.sessions() as db:
            await serialize_write(db)
            if await db.scalar(select(RoundArchive.id).where(RoundArchive.status == "resetting")):
                return Wait(until=context.now + timedelta(seconds=1), checkpoint={})
            evaluation = await db.get(Evaluation, evaluation_id)
            if evaluation is None:
                return Fail(reason="Evaluación no encontrada.")
            if evaluation.status == "running":
                integrity_error = await self._integrity_error(evaluation, db)
                if integrity_error:
                    evaluation.status = "stopped"
                    evaluation.stop_reason = integrity_error
                    evaluation.finished_at = self._fleet.clock()
            rows = list(
                await db.scalars(
                    select(EvaluationExecution)
                    .where(EvaluationExecution.evaluation_id == evaluation_id)
                    .order_by(EvaluationExecution.ordinal)
                )
            )
            completed = {row.ordinal for row in rows if row.status == "completed"}
            total = len(evaluation.cases) * evaluation.repetitions * 2
            if evaluation.status != "running" or len(completed) >= total:
                if evaluation.status == "running":
                    evaluation.status = "completed"
                    evaluation.finished_at = self._fleet.clock()
                evaluation.report = build_report(
                    evaluation,
                    [row.result for row in rows if row.status == "completed"],
                    self._records(evaluation_id),
                )
                await db.commit()
                return Complete(output={"status": evaluation.status, "completed": len(completed)})
            ordinal = next(number for number in range(total) if number not in completed)
            row = await db.get(EvaluationExecution, (evaluation_id, ordinal))
            if row is None:
                row = EvaluationExecution(
                    evaluation_id=evaluation_id,
                    ordinal=ordinal,
                    status="running",
                    starts=0,
                    result={},
                )
                db.add(row)
            row.starts += 1
            row.status = "running"
            starts = row.starts
            await db.commit()
        case = EvaluationCase.model_validate(
            evaluation.cases[(ordinal // 2) % len(evaluation.cases)]
        )
        version = evaluation.before_version if ordinal % 2 == 0 else evaluation.after_version
        repetition = ordinal // (len(evaluation.cases) * 2) + 1
        result = await self._runner.run_case(
            evaluation_id, version, case, repetition, evaluation.max_calls
        )
        result["interrupted_starts"] = starts - 1
        async with self._fleet.database.sessions() as db:
            await serialize_write(db)
            row = await db.get(EvaluationExecution, (evaluation_id, ordinal))
            live = await db.get(Evaluation, evaluation_id)
            if row is None or live is None:
                return Fail(reason="Se perdió la ejecución durable de evaluación.")
            row.status, row.result = "completed", result
            # Respect explicit stop while still keeping evidence from the in-flight case.
            if live.status == "running" and result["error"] in {
                "EvaluationBudgetExceededError",
                "ModelLimitReachedError",
            }:
                live.status = "stopped"
                live.stop_reason = "llm_budget_or_provider_limit"
                live.finished_at = self._fleet.clock()
            elif live.status == "running" and self._consecutive_errors(rows, result):
                live.status = "stopped"
                live.stop_reason = "consecutive_infrastructure_failures"
                live.finished_at = self._fleet.clock()
            await db.commit()
        return Advance(checkpoint={})

    def _records(self, evaluation_id: str) -> list[CallRecord]:
        return [
            record
            for record in self._llm.ledger.records()
            if record.scope.campaign_id == evaluation_id
        ]

    async def _integrity_error(self, evaluation: Evaluation, db: AsyncSession) -> str:
        if canonical_hash(evaluation.cases) != evaluation.metadata_json["suite_hash"]:
            return "suite_integrity_mismatch"
        if fixture_hash() != evaluation.metadata_json["fixture_hash"]:
            return "fixture_integrity_mismatch"
        try:
            for version in (evaluation.before_version, evaluation.after_version):
                policy = await PolicyRepository(db).require(version)
                if policy.content_hash != evaluation.metadata_json["policy_hashes"][str(version)]:
                    return "policy_integrity_mismatch"
        except ValueError:
            return "policy_integrity_mismatch"
        return ""

    def _consecutive_errors(self, rows: list[EvaluationExecution], result: dict[str, Any]) -> bool:
        recent = [row.result for row in rows if row.status == "completed"][-2:]
        return len(recent) == 2 and all(item.get("error") for item in [*recent, result])
