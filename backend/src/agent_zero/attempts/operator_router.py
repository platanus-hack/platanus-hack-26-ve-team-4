from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from agent_zero.attempts.repository import AttemptRepository
from agent_zero.attempts.schemas import AttemptOperatorView
from agent_zero.shared.dependencies import DbSession
from agent_zero.shared.operator_auth import OperatorOnly

router = APIRouter(prefix="/api/operator/attempts", tags=["operator"], dependencies=[OperatorOnly])


@router.get("")
async def list_attempts(
    db: DbSession, limit: Annotated[int, Query(ge=1, le=500)] = 100
) -> list[AttemptOperatorView]:
    attempts = await AttemptRepository(db).list_recent(limit)
    return [AttemptOperatorView.model_validate(attempt) for attempt in attempts]


@router.get("/{attempt_id}")
async def read_attempt(attempt_id: str, db: DbSession) -> AttemptOperatorView:
    attempt = await AttemptRepository(db).get(attempt_id)
    if attempt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No existe el intento {attempt_id}.")
    return AttemptOperatorView.model_validate(attempt)
