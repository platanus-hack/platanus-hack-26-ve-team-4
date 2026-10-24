from fastapi import APIRouter, status

from agent_zero.sessions.dependencies import CurrentSession, SessionTokens
from agent_zero.sessions.schemas import SessionCreate, SessionIssued, SessionRead
from agent_zero.sessions.session_creation_service import create_session
from agent_zero.shared.dependencies import DbSession

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create(payload: SessionCreate, db: DbSession, tokens: SessionTokens) -> SessionIssued:
    session = await create_session(db, payload)
    issued = tokens.issue(session.id)
    return SessionIssued(
        **SessionRead.model_validate(session).model_dump(),
        token=issued.token,
        expires_at=issued.expires_at,
    )


@router.get("/me")
async def me(session: CurrentSession) -> SessionRead:
    return SessionRead.model_validate(session)
