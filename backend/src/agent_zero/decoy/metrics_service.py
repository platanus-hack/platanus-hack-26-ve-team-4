from collections import defaultdict
from statistics import median

from sqlalchemy import select

from agent_zero.attempts.models import Attempt
from agent_zero.config import Settings
from agent_zero.decoy.models import (
    MIN_RATE_N,
    DecoySummary,
    Rate,
    RevealCard,
    SessionTrace,
)
from agent_zero.decoy.session_trace import build_trace
from agent_zero.events.models import EventType
from agent_zero.events.session_events import events_for_sessions
from agent_zero.routing.models import Route
from agent_zero.sessions.models import ArenaSession
from agent_zero.shared.database import Database
from agent_zero.victim.honeytoken import honey_token

TRACE_EVENTS = (EventType.ROUTE_CHANGED, EventType.TOOL_PROPOSED, EventType.TOOL_COMPLETED)


def rate_of(k: int, n: int) -> Rate:
    return Rate(k=k, n=n, value=round(k / n, 4) if n >= MIN_RATE_N else None)


class DecoyMetricsService:
    def __init__(self, database: Database, settings: Settings) -> None:
        self._database = database
        self._key = settings.identity_signing_key.get_secret_value().encode()

    async def _traces(self, only: str | None = None) -> tuple[list[SessionTrace], int]:
        async with self._database.sessions() as db:
            query = select(ArenaSession).where(ArenaSession.route == Route.HONEYPOT)
            if only is not None:
                query = query.where(ArenaSession.id == only)
            sessions = list(await db.scalars(query))
            ids = [session.id for session in sessions]
            events = await events_for_sessions(db, ids, TRACE_EVENTS)
            attempts: dict[str, list[Attempt]] = defaultdict(list)
            if ids:
                rows = await db.scalars(
                    select(Attempt)
                    .where(Attempt.session_id.in_(ids))
                    .order_by(Attempt.created_at, Attempt.id)
                )
                for attempt in rows:
                    attempts[attempt.session_id].append(attempt)
        traces: list[SessionTrace] = []
        excluded = 0
        for session in sessions:
            own = attempts[session.id]
            if any(attempt.origin != "audience" for attempt in own):
                excluded += 1
                continue
            trace = build_trace(
                session_id=session.id,
                alias=session.alias,
                events=events[session.id],
                attempts=own,
                token=honey_token(self._key, session.id),
            )
            if trace is not None:
                traces.append(trace)
        return traces, excluded

    async def summary(self) -> DecoySummary:
        traces, excluded = await self._traces()
        n = len(traces)
        return DecoySummary(
            diverted_n=n,
            excluded_autonomous_n=excluded,
            small_n=n < MIN_RATE_N,
            retained=rate_of(sum(trace.retained for trace in traces), n),
            bait_taken=rate_of(sum(trace.bait_taken for trace in traces), n),
            deceived=rate_of(sum(trace.deceived for trace in traces), n),
            median_retained_seconds=(
                round(median(trace.retained_seconds for trace in traces), 3) if n else None
            ),
            cases=traces,
        )

    async def card_for(self, session_id: str) -> RevealCard | None:
        traces, _ = await self._traces(only=session_id)
        if not traces:
            return None
        trace = traces[0]
        return RevealCard(
            retained_seconds=trace.retained_seconds,
            post_diversion_steps=trace.post_diversion_steps,
            post_diversion_attempts=trace.post_diversion_attempts,
            honeytools_touched=trace.honeytools_touched,
            credential_issued=trace.credential_issued,
            token_reused=trace.token_reused,
        )
