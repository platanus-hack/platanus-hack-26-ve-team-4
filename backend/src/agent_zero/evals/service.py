from typing import Any

from sqlalchemy import func, select

from agent_zero.arena.models import ArenaState
from agent_zero.arena.transactions import serialize_write
from agent_zero.evals.models import Evaluation, EvaluationExecution
from agent_zero.evals.provenance import source_revision
from agent_zero.evals.schemas import EvaluationCreate
from agent_zero.evals.suite import (
    SUITE_VERSION,
    evaluation_suite,
    fixture_hash,
    minimum_calls,
    suite_hash,
)
from agent_zero.fleet.fleet_builder import Fleet
from agent_zero.llm.catalog import model_for
from agent_zero.llm.gateway import LlmGateway
from agent_zero.llm.models import ModelRole
from agent_zero.policies.policy_service import PolicyService
from agent_zero.policies.repository import PolicyRepository
from agent_zero.runtime.run_enqueue_service import RunEnqueueService
from agent_zero.runtime.schemas import RunCreate
from agent_zero.shared.ids import new_id
from agent_zero.victim.arena_manifest import ARENA_VERSION

EVALUATION_HANDLER = "broad_evaluation"


def evaluation_view(row: Evaluation, completed: int) -> dict[str, Any]:
    return {
        "id": row.id,
        "status": row.status,
        "before_version": row.before_version,
        "after_version": row.after_version,
        "repetitions": row.repetitions,
        "max_calls": row.max_calls,
        "total": len(row.cases) * row.repetitions * 2,
        "completed": completed,
        "created_at": row.created_at.isoformat(),
        "finished_at": row.finished_at.isoformat() if row.finished_at else None,
        "stop_reason": row.stop_reason,
        "report": row.report,
        "metadata": row.metadata_json,
    }


class EvaluationService:
    def __init__(self, fleet: Fleet, policies: PolicyService, llm: LlmGateway) -> None:
        self._fleet = fleet
        self._policies = policies
        self._llm = llm

    async def start(self, payload: EvaluationCreate) -> dict[str, Any]:
        cases = evaluation_suite()
        if payload.before_version == payload.after_version:
            raise ValueError("Selecciona dos versiones distintas para comparar.")
        minimum = minimum_calls(cases, payload.repetitions)
        if payload.max_calls < minimum:
            raise ValueError(f"La suite requiere al menos {minimum} llamadas; aumenta max_calls.")
        limits = self._llm.limits
        if payload.max_calls > limits.policy.campaign_calls:
            raise ValueError(
                f"El límite de campaña configurado es {limits.policy.campaign_calls}; "
                f"configura AGENT_ZERO_LLM_CAMPAIGN_CALL_LIMIT al menos en {payload.max_calls}."
            )
        day = self._fleet.clock().date().isoformat()
        if limits.policy.daily_calls - limits.quota.calls(f"day:{day}") < minimum:
            raise ValueError("El presupuesto diario de llamadas no alcanza para la suite completa.")
        if limits.spent_today_usd() >= limits.policy.daily_usd:
            raise ValueError("El presupuesto monetario diario ya está agotado.")
        provenance = source_revision()
        async with self._fleet.database.sessions() as db:
            await serialize_write(db)
            state = await db.get(ArenaState, 1)
            if state is None or not state.accepting:
                raise ValueError("La ronda está cerrada; no se pueden iniciar evaluaciones.")
            if await db.scalar(select(Evaluation.id).where(Evaluation.status == "running")):
                raise ValueError("Ya hay una evaluación en curso.")
            repository = PolicyRepository(db)
            before = await repository.require(payload.before_version)
            after = await repository.require(payload.after_version)
            row = Evaluation(
                id=new_id("eval"),
                status="running",
                before_version=before.version,
                after_version=after.version,
                repetitions=payload.repetitions,
                max_calls=payload.max_calls,
                cases=[case.model_dump(mode="json") for case in cases],
                metadata_json={
                    **provenance,
                    "suite_version": SUITE_VERSION,
                    "suite_hash": suite_hash(cases),
                    "fixture_hash": fixture_hash(),
                    "llm_mode": self._llm.mode.value,
                    "configured_models": {
                        role.value: model_for(role, self._fleet.settings) for role in ModelRole
                    },
                    "policy_hashes": {
                        str(before.version): before.content_hash,
                        str(after.version): after.content_hash,
                    },
                    "policy_rules": {
                        str(before.version): before.rules,
                        str(after.version): after.rules,
                    },
                    "created_at": self._fleet.clock().isoformat(),
                    "honeypot_enabled": False,
                    "minimum_calls": minimum,
                },
                report={},
                stop_reason="",
                created_at=self._fleet.clock(),
                finished_at=None,
            )
            db.add(row)
            await RunEnqueueService(db, self._fleet.handlers, self._fleet.clock).enqueue(
                RunCreate(
                    agent_id="prober",
                    agent_version=ARENA_VERSION,
                    handler=EVALUATION_HANDLER,
                    input={"evaluation_id": row.id},
                    idempotency_key=f"evaluation:{row.id}",
                ),
                commit=False,
            )
            await db.commit()
            return evaluation_view(row, 0)

    async def all(self) -> list[dict[str, Any]]:
        async with self._fleet.database.sessions() as db:
            result = []
            for row in await db.scalars(select(Evaluation).order_by(Evaluation.created_at.desc())):
                completed = await db.scalar(
                    select(func.count())
                    .select_from(EvaluationExecution)
                    .where(
                        EvaluationExecution.evaluation_id == row.id,
                        EvaluationExecution.status == "completed",
                    )
                )
                result.append(evaluation_view(row, completed or 0))
            return result

    async def get(self, evaluation_id: str) -> dict[str, Any]:
        async with self._fleet.database.sessions() as db:
            row = await db.get(Evaluation, evaluation_id)
            if row is None:
                raise ValueError("Evaluación no encontrada.")
            results = [
                item.result
                for item in await db.scalars(
                    select(EvaluationExecution)
                    .where(
                        EvaluationExecution.evaluation_id == evaluation_id,
                        EvaluationExecution.status == "completed",
                    )
                    .order_by(EvaluationExecution.ordinal)
                )
            ]
            return evaluation_view(row, len(results)) | {"results": results, "cases": row.cases}

    async def stop(self, evaluation_id: str) -> dict[str, Any]:
        async with self._fleet.database.sessions() as db:
            await serialize_write(db)
            row = await db.get(Evaluation, evaluation_id)
            if row is None:
                raise ValueError("Evaluación no encontrada.")
            if row.status == "running":
                row.status = "stopped"
                row.stop_reason = "operator_stopped"
                row.finished_at = self._fleet.clock()
                await db.commit()
        return await self.get(evaluation_id)
