from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from agent_zero.arena.arena_service import ArenaService
from agent_zero.arena.dependencies import Core
from agent_zero.arena.round_models import RoundArchive
from agent_zero.registry.dependencies import OperatorOnly

router = APIRouter(prefix="/api/operator", tags=["operator"], dependencies=[OperatorOnly])


class ResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    reason: str = Field(min_length=1, max_length=500)


@router.post("/reset")
@router.post("/arena/reset")
async def reset(payload: ResetRequest, core: Core) -> dict[str, Any]:
    async with core.maintenance_lock:
        await core.worker.stop()
        await core.fleet.worker.stop()
        try:
            async with core.admission_lock:
                archive_id = await core.rounds.reset(payload.reason)
        except ValueError as error:
            raise HTTPException(409, str(error)) from error
        finally:
            async with core.fleet.database.sessions() as db:
                unfinished = await db.scalar(
                    select(RoundArchive.id).where(RoundArchive.status == "resetting").limit(1)
                )
            if unfinished is None:
                core.fleet.worker.start()
                core.worker.start()
    state = await ArenaService(
        core.fleet.database, core.attempts, core.policies, core.fleet.settings
    ).state()
    return state | {"archive_id": archive_id}


@router.get("/rounds")
async def archives(core: Core) -> list[dict[str, Any]]:
    return await core.rounds.archives()


@router.get("/rounds/{archive_id}/archive")
async def archive(archive_id: str, core: Core) -> dict[str, Any]:
    try:
        result = await core.rounds.archive(archive_id)
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    if result is None:
        raise HTTPException(404, "Archivo no encontrado.")
    return result
