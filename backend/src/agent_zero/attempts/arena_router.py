from fastapi import APIRouter, Request

from agent_zero.attempts.arena_state import ArenaState, arena_state
from agent_zero.attempts.execution import ArenaWiring
from agent_zero.attempts.repository import AttemptRepository
from agent_zero.shared.dependencies import DbSession

router = APIRouter(prefix="/api/arena", tags=["arena"])


@router.get("/state")
async def read_state(request: Request, db: DbSession) -> ArenaState:
    wiring: ArenaWiring = request.app.state.arena
    return arena_state(await AttemptRepository(db).tally(), wiring.policy_version())
