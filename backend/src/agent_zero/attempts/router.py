from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status

from agent_zero.attempts.dependencies import Submissions
from agent_zero.attempts.errors import (
    AttemptRejectedError,
    QueueFullError,
    TargetUnavailableError,
    TooFrequentError,
)
from agent_zero.attempts.repository import AttemptRepository
from agent_zero.attempts.schemas import AttemptCreate, AttemptPublicView
from agent_zero.sessions.dependencies import CurrentSession
from agent_zero.shared.dependencies import DbSession

router = APIRouter(prefix="/api/attempts", tags=["attempts"])

REJECTION_STATUS: dict[type[AttemptRejectedError], int] = {
    TooFrequentError: status.HTTP_429_TOO_MANY_REQUESTS,
    QueueFullError: status.HTTP_503_SERVICE_UNAVAILABLE,
    TargetUnavailableError: status.HTTP_503_SERVICE_UNAVAILABLE,
}


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def submit(
    payload: AttemptCreate, session: CurrentSession, submissions: Submissions, response: Response
) -> AttemptPublicView:
    try:
        submission = await submissions.submit(session, payload)
    except AttemptRejectedError as error:
        headers = {"Retry-After": str(error.retry_after)} if error.retry_after else None
        raise HTTPException(REJECTION_STATUS[type(error)], error.detail, headers=headers) from error
    if not submission.created:
        response.status_code = status.HTTP_200_OK
    return AttemptPublicView.of(submission.attempt)


@router.get("")
async def list_mine(
    session: CurrentSession, db: DbSession, limit: Annotated[int, Query(ge=1, le=100)] = 50
) -> list[AttemptPublicView]:
    attempts = await AttemptRepository(db).list_by_session(session.id, limit)
    return [AttemptPublicView.of(attempt) for attempt in attempts]


@router.get("/{attempt_id}")
async def read(attempt_id: str, session: CurrentSession, db: DbSession) -> AttemptPublicView:
    attempt = await AttemptRepository(db).get(attempt_id)
    # Un intento ajeno responde igual que uno inexistente: no se confirma que exista.
    if attempt is None or attempt.session_id != session.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No existe el intento {attempt_id}.")
    return AttemptPublicView.of(attempt)
