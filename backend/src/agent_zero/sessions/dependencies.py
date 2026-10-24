from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request

from agent_zero.sessions.models import ArenaSession
from agent_zero.sessions.repository import SessionRepository
from agent_zero.sessions.session_token import InvalidSessionTokenError, SessionTokens
from agent_zero.shared.dependencies import DbSession


async def current_session(
    request: Request,
    db: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> ArenaSession:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Necesitas el token de tu sesión.")
    try:
        session_id = SessionTokens(request.app.state.settings).verify(authorization[7:])
    except InvalidSessionTokenError as error:
        raise HTTPException(401, str(error)) from error
    session = await SessionRepository(db).get(session_id)
    if session is None:
        raise HTTPException(401, "La sesión ya no está disponible.")
    return session


CurrentSession = Annotated[ArenaSession, Depends(current_session)]
