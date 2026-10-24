from fastapi import APIRouter, status

from agent_zero.sessions.schemas import SessionCreate, SessionRead
from agent_zero.sessions.session_creation_service import create_session
from agent_zero.shared.dependencies import DbSession

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create(payload: SessionCreate, db: DbSession) -> SessionRead:
    session = await create_session(db, payload)
    return SessionRead.model_validate(session)
