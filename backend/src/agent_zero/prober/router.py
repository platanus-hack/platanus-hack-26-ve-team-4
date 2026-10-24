from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from agent_zero.arena.dependencies import Core
from agent_zero.prober.campaign_service import CampaignService
from agent_zero.registry.dependencies import OperatorOnly

router = APIRouter(prefix="/api/operator/campaigns", tags=["prober"], dependencies=[OperatorOnly])


class CampaignCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_attempts: int = Field(default=9, ge=1, le=30)


@router.post("", status_code=202)
async def start(payload: CampaignCreate, core: Core) -> dict[str, Any]:
    await core.ensure_agents()
    async with core.admission_lock:
        try:
            return await CampaignService(core.fleet).start(payload.max_attempts)
        except ValueError as error:
            raise HTTPException(409, str(error)) from error


@router.get("")
async def campaigns(core: Core) -> list[dict[str, Any]]:
    return await CampaignService(core.fleet).all()


@router.post("/{campaign_id}/stop")
async def stop(campaign_id: str, core: Core) -> dict[str, Any]:
    try:
        return await CampaignService(core.fleet).stop(campaign_id)
    except ValueError as error:
        raise HTTPException(404, str(error)) from error
