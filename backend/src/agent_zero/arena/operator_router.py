from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from agent_zero.arena.arena_service import ArenaService
from agent_zero.arena.dependencies import Core
from agent_zero.attempts.attempt_query_service import attempt_view
from agent_zero.attempts.schemas import AttemptCreate
from agent_zero.prober.campaign_service import CampaignService
from agent_zero.registry.dependencies import OperatorOnly
from agent_zero.sessions.session_query_service import internal_session
from agent_zero.shared.ids import new_id

router = APIRouter(prefix="/api/operator", tags=["operator"], dependencies=[OperatorOnly])


class RollbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=1, max_length=500)


@router.get("/policies")
async def policies(core: Core) -> list[dict[str, Any]]:
    return await core.policies.all()


@router.get("/findings")
async def findings(core: Core) -> list[dict[str, Any]]:
    return await core.findings.all()


@router.get("/attempts")
async def attempts(core: Core) -> list[dict[str, Any]]:
    return [attempt_view(attempt, operator=True) for attempt in await core.attempts.all()]


@router.get("/attempts/{attempt_id}")
async def evidence(attempt_id: str, core: Core) -> dict[str, Any]:
    attempt = await core.attempts.get(attempt_id)
    if attempt is None:
        raise HTTPException(404, "Intento no encontrado.")
    return attempt_view(attempt, operator=True) | {
        "events": [
            event.model_dump(mode="json") for event in await core.events.for_attempt(attempt_id)
        ]
    }


@router.post("/attempts/{attempt_id}/replay", status_code=202)
async def replay(attempt_id: str, core: Core) -> dict[str, Any]:
    attempt = await core.attempts.get(attempt_id)
    if attempt is None:
        raise HTTPException(404, "Intento no encontrado.")
    async with core.fleet.database.sessions() as db:
        session = await internal_session(db, attempt.customer_id, "Repetición")
    repeated = await core.submissions.submit(
        session.id,
        AttemptCreate(
            messages=attempt.messages,
            objective_id=attempt.objective_id,
            idempotency_key=new_id("replay"),
        ),
        origin="autonomous",
    )
    return attempt_view(repeated, operator=True)


@router.post("/policies/{version}/rollback")
async def rollback(version: int, payload: RollbackRequest, core: Core) -> dict[str, int]:
    try:
        target = await core.policies.rollback(version, payload.reason, core.attempts.drained)
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    parent = await core.policies.get(target)
    await core.findings.reconcile_after_rollback(parent["rules"])
    return {"active_version": target}


@router.post("/arena/{action}")
async def control(action: str, core: Core) -> dict[str, Any]:
    service = ArenaService(core.fleet.database, core.attempts, core.policies)
    async with core.admission_lock:
        if action == "pause":
            return await service.set_state(accepting=False)
        if action == "resume":
            try:
                return await service.set_state(accepting=True)
            except ValueError as error:
                raise HTTPException(409, str(error)) from error
        if action == "reveal":
            if not await core.attempts.drained():
                raise HTTPException(409, "Espera a que terminen los intentos antes de revelar.")
            campaigns = CampaignService(core.fleet)
            for campaign in await campaigns.all():
                if campaign["status"] == "running":
                    await campaigns.stop(campaign["id"])
            return await service.set_state(revealed=True)
    raise HTTPException(404, "Control desconocido.")
