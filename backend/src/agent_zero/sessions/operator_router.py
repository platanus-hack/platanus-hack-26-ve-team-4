from fastapi import APIRouter

from agent_zero.sessions.repository import SessionRepository
from agent_zero.sessions.schemas import SessionOperatorView
from agent_zero.shared.dependencies import DbSession
from agent_zero.shared.operator_auth import OperatorOnly

router = APIRouter(prefix="/api/operator/sessions", tags=["operator"], dependencies=[OperatorOnly])


@router.get("")
async def list_sessions(db: DbSession) -> list[SessionOperatorView]:
    sessions = await SessionRepository(db).list_all()
    return [SessionOperatorView.model_validate(session) for session in sessions]
