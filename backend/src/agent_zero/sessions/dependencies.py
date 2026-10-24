from datetime import timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from agent_zero.config import Settings
from agent_zero.sessions.models import ArenaSession
from agent_zero.sessions.repository import SessionRepository
from agent_zero.sessions.session_token import SessionTokenCodec, SessionTokenError
from agent_zero.shared.dependencies import DbSession

_bearer = HTTPBearer(auto_error=False)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED, detail, headers={"WWW-Authenticate": "Bearer"}
    )


def get_session_tokens(request: Request) -> SessionTokenCodec:
    settings: Settings = request.app.state.settings
    return SessionTokenCodec(
        settings.session_signing_key.get_secret_value().encode("utf-8"),
        timedelta(seconds=settings.session_token_ttl_seconds),
    )


SessionTokens = Annotated[SessionTokenCodec, Depends(get_session_tokens)]


async def current_session(
    db: DbSession,
    tokens: SessionTokens,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> ArenaSession:
    if credentials is None:
        raise _unauthorized("Falta el token de sesión.")
    try:
        session_id = tokens.verify(credentials.credentials)
    except SessionTokenError:
        raise _unauthorized("Token de sesión inválido o vencido.") from None
    session = await SessionRepository(db).get(session_id)
    if session is None:
        raise _unauthorized("La sesión ya no existe.")
    return session


CurrentSession = Annotated[ArenaSession, Depends(current_session)]
