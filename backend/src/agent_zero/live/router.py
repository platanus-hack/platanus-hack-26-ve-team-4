from typing import Annotated

from fastapi import APIRouter, Query, Request

from agent_zero.arena.dependencies import Core
from agent_zero.live.models import LiveBoard
from agent_zero.live.service import LiveBoardService
from agent_zero.llm.gateway import LlmGateway
from agent_zero.registry.dependencies import OperatorOnly

router = APIRouter(prefix="/api/operator", tags=["operator"], dependencies=[OperatorOnly])


@router.get("/live")
async def live(
    core: Core, request: Request, sessions: Annotated[int, Query(ge=1, le=12)] = 6
) -> LiveBoard:
    llm: LlmGateway = request.app.state.llm
    service = LiveBoardService(core, llm)
    return await service.board(sessions)
