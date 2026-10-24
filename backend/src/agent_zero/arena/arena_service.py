from typing import Any

from sqlalchemy import func, select

from agent_zero.analyzer.models import FindingRecord, FindingStatus
from agent_zero.arena.models import ArenaState
from agent_zero.arena.round_models import RoundArchive, RoundMetadata
from agent_zero.arena.scoring import SCORED_OUTCOMES, ScoredAttempt, build_scores, reveal_counts
from agent_zero.arena.transactions import serialize_write
from agent_zero.attempts.attempt_query_service import AttemptQueryService
from agent_zero.attempts.models import Attempt, AttemptOutcome, AttemptStatus
from agent_zero.config import Settings
from agent_zero.policies.policy_service import PolicyService
from agent_zero.policies.repository import PolicyRepository
from agent_zero.sessions.models import ArenaSession
from agent_zero.sessions.session_query_service import session_aliases
from agent_zero.shared.database import Database, begin_snapshot


class ArenaService:
    def __init__(
        self,
        database: Database,
        attempts: AttemptQueryService,
        policies: PolicyService,
        settings: Settings | None = None,
    ) -> None:
        self._database = database
        self._attempts = attempts
        self._policies = policies
        self._settings = settings

    async def state(self) -> dict[str, Any]:
        async with self._database.sessions() as db:
            await begin_snapshot(db)
            state = await db.get(ArenaState, 1)
            if state is None:
                raise ValueError("Arena no inicializada.")
            metadata = await db.get(RoundMetadata, 1)
            scored = [
                ScoredAttempt.of(attempt)
                for attempt in await db.scalars(
                    select(Attempt).where(
                        Attempt.origin == "audience", Attempt.outcome.in_(SCORED_OUTCOMES)
                    )
                )
            ]
            aliases = await session_aliases(db, {attempt.session_id for attempt in scored})
            statuses = dict(
                (
                    await db.execute(select(Attempt.status, func.count()).group_by(Attempt.status))
                ).all()
            )
            origins = dict(
                (
                    await db.execute(select(Attempt.origin, func.count()).group_by(Attempt.origin))
                ).all()
            )
            mode = self._settings.llm_mode.value if self._settings is not None else "unknown"
            return {
                "accepting": state.accepting,
                "revealed": state.revealed,
                "provisional": not state.revealed,
                "round_id": metadata.round_id if metadata else None,
                "started_at": metadata.started_at.isoformat() if metadata else None,
                "resetting": await db.scalar(
                    select(RoundArchive.id).where(RoundArchive.status == "resetting").limit(1)
                )
                is not None,
                "session_count": int(
                    await db.scalar(
                        select(func.count())
                        .select_from(ArenaSession)
                        .where(ArenaSession.id.startswith("sess-"))
                    )
                    or 0
                ),
                "session_limit": self._settings.arena_session_limit if self._settings else None,
                "policy_version": (await PolicyRepository(db).active()).version,
                "attempts": sum(statuses.values()),
                "audience_attempts": origins.get("audience", 0),
                "autonomous_attempts": origins.get("autonomous", 0),
                "queued_attempts": statuses.get(AttemptStatus.QUEUED, 0),
                "running_attempts": statuses.get(AttemptStatus.RUNNING, 0),
                "evaluated_attempts": statuses.get(AttemptStatus.EVALUATED, 0),
                "inconclusive_attempts": statuses.get(AttemptStatus.INCONCLUSIVE, 0),
                "prevented_attempts": int(
                    await db.scalar(
                        select(func.count())
                        .select_from(Attempt)
                        .where(Attempt.outcome == AttemptOutcome.PREVENTED)
                    )
                    or 0
                ),
                "open_findings": int(
                    await db.scalar(
                        select(func.count())
                        .select_from(FindingRecord)
                        .where(
                            FindingRecord.status.in_([FindingStatus.OPEN, FindingStatus.REOPENED])
                        )
                    )
                    or 0
                ),
                "llm_mode": mode,
                "evidence_mode": (
                    "live"
                    if mode in {"live", "record"}
                    else "replayed"
                    if mode == "replay"
                    else "simulated"
                ),
                "demo_mode": mode == "demo",
                "scores": build_scores(scored, aliases, revealed=state.revealed),
                **(reveal_counts(scored) if state.revealed else {}),
            }

    async def set_state(
        self, *, accepting: bool | None = None, revealed: bool | None = None
    ) -> dict[str, Any]:
        async with self._database.sessions() as db:
            await serialize_write(db)
            state = await db.get(ArenaState, 1)
            if state is None:
                raise ValueError("Arena no inicializada.")
            if accepting is not None:
                if accepting and state.revealed:
                    raise ValueError(
                        "La ronda revelada está cerrada. Reinicia para un ensayo nuevo."
                    )
                if (
                    accepting
                    and await db.scalar(
                        select(RoundArchive.id).where(RoundArchive.status == "resetting").limit(1)
                    )
                    is not None
                ):
                    raise ValueError("El reinicio de la ronda todavía no terminó.")
                state.accepting = accepting
            if revealed is not None:
                state.revealed = revealed
                if revealed:
                    state.accepting = False
            await db.commit()
        return await self.state()
