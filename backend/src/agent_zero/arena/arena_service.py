from typing import Any

from agent_zero.arena.models import ArenaState
from agent_zero.attempts.attempt_query_service import AttemptQueryService
from agent_zero.attempts.models import AttemptOutcome
from agent_zero.policies.policy_service import PolicyService
from agent_zero.sessions.session_query_service import query_session
from agent_zero.shared.database import Database


class ArenaService:
    def __init__(
        self, database: Database, attempts: AttemptQueryService, policies: PolicyService
    ) -> None:
        self._database = database
        self._attempts = attempts
        self._policies = policies

    async def state(self) -> dict[str, Any]:
        async with self._database.sessions() as db:
            state = await db.get(ArenaState, 1)
            if state is None:
                raise ValueError("Arena no inicializada.")
            scores: dict[str, set[tuple[str, int]]] = {}
            aliases: dict[str, str] = {}
            attempts = await self._attempts.all()
            for attempt in attempts:
                if attempt.origin != "audience":
                    continue
                apparent = (
                    not state.revealed and attempt.outcome is AttemptOutcome.CONTAINED_HONEYPOT
                )
                if attempt.outcome is AttemptOutcome.CONFIRMED_VIOLATION or apparent:
                    for verdict in attempt.assessment.get("verdicts", []):
                        if verdict["violated"]:
                            scores.setdefault(attempt.session_id, set()).add(
                                (verdict["objective_id"], attempt.policy_version)
                            )
                    session = await query_session(db, attempt.session_id)
                    if session:
                        aliases[attempt.session_id] = session.alias
            return {
                "accepting": state.accepting,
                "revealed": state.revealed,
                "provisional": not state.revealed,
                "policy_version": await self._policies.active_version(),
                "attempts": len(attempts),
                "scores": sorted(
                    [
                        {"alias": aliases.get(session, "Participante"), "score": len(points)}
                        for session, points in scores.items()
                        if points
                    ],
                    key=lambda item: (-int(item["score"]), str(item["alias"])),
                ),
            }

    async def set_state(
        self, *, accepting: bool | None = None, revealed: bool | None = None
    ) -> dict[str, Any]:
        async with self._database.sessions() as db:
            state = await db.get(ArenaState, 1)
            if state is None:
                raise ValueError("Arena no inicializada.")
            if accepting is not None:
                if accepting and state.revealed:
                    raise ValueError("La ronda revelada está cerrada. Inicia un ensayo nuevo.")
                state.accepting = accepting
            if revealed is not None:
                state.revealed = revealed
                if revealed:
                    state.accepting = False
            await db.commit()
        return await self.state()
