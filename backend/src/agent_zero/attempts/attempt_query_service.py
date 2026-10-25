from typing import Any

from sqlalchemy import select

from agent_zero.agent_gateway.business_policy import CallContext
from agent_zero.arena.models import ArenaState
from agent_zero.attempts.conversation import links_for, public_reply
from agent_zero.attempts.models import Attempt, AttemptOutcome
from agent_zero.attempts.repository import AttemptRepository
from agent_zero.shared.database import Database


def call_context(attempt: Attempt) -> CallContext:
    return CallContext(
        attempt_id=attempt.id,
        session_id=attempt.session_id,
        session_customer_id=attempt.customer_id,
        environment=attempt.route.value,
        policy_version=attempt.policy_version,
        run_id=attempt.run_id,
        campaign_id=attempt.campaign_id,
    )


def attempt_view(
    attempt: Attempt, *, operator: bool = False, revealed: bool = False
) -> dict[str, Any]:
    outcome = attempt.outcome.value if attempt.outcome else None
    if (
        not operator
        and not revealed
        and attempt.outcome
        in {
            AttemptOutcome.CONFIRMED_VIOLATION,
            AttemptOutcome.CONTAINED_HONEYPOT,
        }
    ):
        outcome = "apparent_success"
    result: dict[str, Any] = {
        "id": attempt.id,
        "status": attempt.status.value,
        "outcome": outcome,
        "policy_version": attempt.policy_version,
        "reply": public_reply(attempt.reply),
        "created_at": attempt.created_at.isoformat(),
        "updated_at": attempt.updated_at.isoformat(),
        "messages": attempt.messages,
        "idempotency_key": attempt.idempotency_key,
    }
    if operator:
        result.update(
            session_id=attempt.session_id,
            route=attempt.route.value,
            run_id=attempt.run_id,
            messages=attempt.messages,
            customer_id=attempt.customer_id,
            assessment=attempt.assessment,
            origin=attempt.origin,
        )
    return result


class AttemptQueryService:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def get(self, attempt_id: str) -> Attempt | None:
        async with self._database.sessions() as db:
            return await AttemptRepository(db).get(attempt_id)

    async def revealed(self) -> bool:
        async with self._database.sessions() as db:
            state = await db.get(ArenaState, 1)
            return state is not None and state.revealed

    async def drained(self) -> bool:
        async with self._database.sessions() as db:
            return await AttemptRepository(db).in_flight() == 0

    async def none_running(self) -> bool:
        async with self._database.sessions() as db:
            return await AttemptRepository(db).running() == 0

    async def needs_diversion(self, session_id: str) -> bool:
        async with self._database.sessions() as db:
            return await AttemptRepository(db).needs_diversion(session_id)

    async def for_session(self, session_id: str) -> list[Attempt]:
        async with self._database.sessions() as db:
            return list(
                await db.scalars(
                    select(Attempt)
                    .where(Attempt.session_id == session_id)
                    .order_by(Attempt.created_at, Attempt.id)
                )
            )

    async def links(self, attempt_ids: list[str]) -> dict[str, str]:
        async with self._database.sessions() as db:
            return await links_for(db, attempt_ids)

    async def all(self) -> list[Attempt]:
        async with self._database.sessions() as db:
            return list(await db.scalars(select(Attempt).order_by(Attempt.created_at)))
