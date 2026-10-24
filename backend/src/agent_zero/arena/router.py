from typing import Any

from fastapi import APIRouter

from agent_zero.arena.arena_service import ArenaService
from agent_zero.arena.dependencies import Core

router = APIRouter(prefix="/api/arena", tags=["arena"])


@router.get("/state")
async def state(core: Core) -> dict[str, Any]:
    return await ArenaService(core.fleet.database, core.attempts, core.policies).state()
