from typing import Any, Literal, Self

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator

from agent_zero.arena.dependencies import Core
from agent_zero.prober.campaign_service import CampaignService
from agent_zero.registry.dependencies import OperatorOnly

router = APIRouter(prefix="/api/operator/campaigns", tags=["prober"], dependencies=[OperatorOnly])


class CampaignCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_attempts: int = Field(default=9, ge=1, le=60)
    generation: Literal["templates", "llm", "adaptive"] = "templates"
    max_mutations: int = Field(default=30, ge=1, le=30)

    @model_validator(mode="after")
    def non_adaptive_budget(self) -> Self:
        if self.generation != "adaptive" and self.max_attempts > 30:
            raise ValueError("Solo la generación adaptive admite más de treinta casos.")
        return self


@router.post("", status_code=202)
async def start(payload: CampaignCreate, core: Core) -> dict[str, Any]:
    await core.ensure_agents()
    async with core.admission_lock:
        try:
            return await CampaignService(core.fleet).start(
                payload.max_attempts, payload.generation, payload.max_mutations
            )
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
