from fastapi import APIRouter, HTTPException, status

from agent_zero.runtime.dependencies import Registry, RuntimeClock
from agent_zero.runtime.handler_registry import UnknownHandlerError
from agent_zero.runtime.repository import RunRepository
from agent_zero.runtime.run_cancel_service import RunCancelService, RunNotFoundError
from agent_zero.runtime.run_enqueue_service import RunEnqueueService
from agent_zero.runtime.schemas import RunAccepted, RunCreate, RunRead
from agent_zero.shared.dependencies import DbSession

router = APIRouter(prefix="/api/runtime/runs", tags=["runtime"])


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def enqueue(
    payload: RunCreate, db: DbSession, registry: Registry, clock: RuntimeClock
) -> RunAccepted:
    try:
        run = await RunEnqueueService(db, registry, clock).enqueue(payload)
    except UnknownHandlerError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
    return RunAccepted(run_id=run.run_id, status=run.status)


@router.get("/{run_id}")
async def read(run_id: str, db: DbSession) -> RunRead:
    run = await RunRepository(db).get(run_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No existe la ejecución {run_id}.")
    return RunRead.model_validate(run)


@router.post("/{run_id}/cancel")
async def cancel(run_id: str, db: DbSession, clock: RuntimeClock) -> RunRead:
    try:
        run = await RunCancelService(db, clock).cancel(run_id)
    except RunNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    return RunRead.model_validate(run)
