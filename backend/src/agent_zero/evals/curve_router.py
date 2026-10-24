from typing import Any

from fastapi import APIRouter

from agent_zero.arena.dependencies import Core
from agent_zero.evals.round_curve import coevolution
from agent_zero.shared.database import begin_snapshot

router = APIRouter(prefix="/api/arena", tags=["arena"])


@router.get("/coevolution")
async def curve(core: Core) -> dict[str, Any]:
    async with core.fleet.database.sessions() as db:
        await begin_snapshot(db)
        return await coevolution(db, core.fleet.settings)
