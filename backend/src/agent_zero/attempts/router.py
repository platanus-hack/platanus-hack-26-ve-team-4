from typing import Any

from fastapi import APIRouter, HTTPException

from agent_zero.arena.dependencies import Core
from agent_zero.attempts.attempt_query_service import attempt_view
from agent_zero.attempts.schemas import AttemptCreate
from agent_zero.sessions.dependencies import CurrentSession

router = APIRouter(prefix="/api/attempts", tags=["attempts"])


@router.post("", status_code=202)
async def submit(payload: AttemptCreate, session: CurrentSession, core: Core) -> dict[str, Any]:
    await core.ensure_agents()
    return attempt_view(await core.submissions.submit(session.id, payload))


@router.get("/{attempt_id}")
async def get_attempt(attempt_id: str, session: CurrentSession, core: Core) -> dict[str, Any]:
    attempt = await core.attempts.get(attempt_id)
    if attempt is None or attempt.session_id != session.id:
        raise HTTPException(404, "Intento no encontrado.")
    return attempt_view(attempt)
