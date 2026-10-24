from typing import Any

from fastapi import APIRouter, HTTPException

from agent_zero.arena.dependencies import Core
from agent_zero.evals.schemas import EvaluationCreate
from agent_zero.registry.dependencies import OperatorOnly

router = APIRouter(
    prefix="/api/operator/evaluations", tags=["evaluation"], dependencies=[OperatorOnly]
)


@router.post("", status_code=202)
async def start(payload: EvaluationCreate, core: Core) -> dict[str, Any]:
    await core.ensure_agents()
    async with core.admission_lock:
        try:
            return await core.evaluations.start(payload)
        except ValueError as error:
            raise HTTPException(409, str(error)) from error


@router.get("")
async def evaluations(core: Core) -> list[dict[str, Any]]:
    return await core.evaluations.all()


@router.get("/{evaluation_id}")
async def evaluation(evaluation_id: str, core: Core) -> dict[str, Any]:
    try:
        return await core.evaluations.get(evaluation_id)
    except ValueError as error:
        raise HTTPException(404, str(error)) from error


@router.post("/{evaluation_id}/stop")
async def stop(evaluation_id: str, core: Core) -> dict[str, Any]:
    try:
        return await core.evaluations.stop(evaluation_id)
    except ValueError as error:
        raise HTTPException(404, str(error)) from error
