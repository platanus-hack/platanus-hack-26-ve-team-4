import asyncio
import math
from datetime import datetime, timedelta
from typing import Literal

from fastapi import HTTPException

from agent_zero.arena.models import ArenaState
from agent_zero.arena.transactions import serialize_write
from agent_zero.attempts.conversation import check_continuation, links_for
from agent_zero.attempts.models import Attempt, AttemptLink, AttemptStatus
from agent_zero.attempts.repository import AttemptRepository
from agent_zero.attempts.schemas import AttemptCreate
from agent_zero.events.event_store import EventStore
from agent_zero.events.models import EventType
from agent_zero.events.schemas import EventDraft
from agent_zero.fleet.fleet_builder import Fleet
from agent_zero.policies.policy_service import PolicyService
from agent_zero.policies.repository import PolicyRepository
from agent_zero.prober.campaign_models import Campaign
from agent_zero.routing.route_decision_service import RouteDecisionService
from agent_zero.runtime.run_enqueue_service import RunEnqueueService
from agent_zero.runtime.schemas import RunCreate
from agent_zero.sessions.session_query_service import query_session
from agent_zero.shared.ids import new_id
from agent_zero.victim.arena_manifest import ARENA_HANDLER, ARENA_VERSION

RATE_WINDOW = timedelta(minutes=1)
# A full queue has no known release time: it frees when a pending attempt finishes, which
# usually takes a few seconds. Five seconds matches the participant UI fallback.
QUEUE_RETRY_SECONDS = 5


def retry_after_seconds(release: datetime, now: datetime) -> int:
    """Whole seconds until `release`, at least 1 so a client never retries immediately."""
    return max(1, math.ceil((release - now).total_seconds()))


class AttemptSubmissionService:
    def __init__(
        self,
        fleet: Fleet,
        policies: PolicyService,
        events: EventStore,
        routing: RouteDecisionService,
        lock: asyncio.Lock,
    ) -> None:
        self._fleet = fleet
        self._policies = policies
        self._events = events
        self._routing = routing
        self._lock = lock

    async def submit(
        self,
        session_id: str,
        payload: AttemptCreate,
        origin: Literal["audience", "autonomous"] = "audience",
        campaign_id: str | None = None,
    ) -> Attempt:
        async with self._lock, self._fleet.database.sessions() as db:
            await serialize_write(db)
            repository = AttemptRepository(db)
            existing = await repository.by_key(session_id, payload.idempotency_key)
            if existing is not None:
                previous = (await links_for(db, [existing.id])).get(existing.id)
                if (
                    existing.messages,
                    existing.objective_id,
                    existing.origin,
                    existing.campaign_id,
                    previous,
                ) != (payload.turns, payload.objective_id, origin, campaign_id, payload.continues):
                    raise HTTPException(
                        409, "La clave de idempotencia ya corresponde a otro intento."
                    )
                return existing
            if campaign_id is not None:
                campaign = await db.get(Campaign, campaign_id)
                if campaign is None or campaign.status != "running" or origin != "autonomous":
                    raise HTTPException(409, "La campaña ya no admite nuevos intentos.")
            session = await query_session(db, session_id)
            if session is None:
                raise HTTPException(401, "Sesión no disponible.")
            if payload.continues is not None:
                await check_continuation(db, session_id, payload.continues)
            state = await db.get(ArenaState, 1)
            if state is None or not state.accepting:
                raise HTTPException(409, "Las entradas de la ronda están cerradas.")
            settings = self._fleet.settings
            if (
                await repository.in_flight(origin=origin) >= settings.arena_queue_limit
                or await repository.in_flight(session_id) >= settings.arena_session_queue_limit
            ):
                raise HTTPException(
                    429,
                    "La cola está llena; espera el resultado anterior.",
                    headers={"Retry-After": str(QUEUE_RETRY_SECONDS)},
                )
            now = self._fleet.clock()
            recent = await repository.created_since(session_id, now - RATE_WINDOW)
            limit = settings.arena_attempts_per_minute
            if len(recent) >= limit:
                # Admission reopens once enough attempts leave the window to drop below the limit.
                release = recent[len(recent) - limit] + RATE_WINDOW
                raise HTTPException(
                    429,
                    "Alcanzaste el límite de intentos por minuto.",
                    headers={"Retry-After": str(retry_after_seconds(release, now))},
                )
            route = await self._routing.decide(session, payload.turns, db)
            version = (await PolicyRepository(db).active()).version
            attempt_id = new_id("attempt")
            run = await RunEnqueueService(db, self._fleet.handlers, self._fleet.clock).enqueue(
                RunCreate(
                    agent_id="soporte-senuelo" if route.value == "honeypot" else "soporte-tienda",
                    agent_version=ARENA_VERSION,
                    handler=ARENA_HANDLER,
                    input={"attempt_id": attempt_id},
                    idempotency_key=f"attempt:{attempt_id}",
                ),
                commit=False,
            )
            attempt = Attempt(
                id=attempt_id,
                session_id=session_id,
                customer_id=session.customer_id,
                origin=origin,
                campaign_id=campaign_id,
                policy_version=version,
                route=route,
                run_id=run.run_id,
                idempotency_key=payload.idempotency_key,
                messages=payload.turns,
                objective_id=payload.objective_id,
                status=AttemptStatus.QUEUED,
                assessment={},
                reply="",
                created_at=now,
                updated_at=now,
            )
            db.add(attempt)
            if payload.continues is not None:
                db.add(AttemptLink(attempt_id=attempt_id, previous_attempt_id=payload.continues))
            await self._events.stage(
                db,
                EventDraft(
                    type=EventType.ATTEMPT_QUEUED,
                    attempt_id=attempt.id,
                    session_id=session_id,
                    policy_version=version,
                    data={"origin": origin},
                ),
                dedup_key=f"{attempt.id}:queued",
            )
            await self._events.stage_public(
                db,
                EventType.ATTEMPT_QUEUED,
                version,
                status="queued",
                dedup_key=f"{attempt.id}:queued:public",
            )
            await db.commit()
        await self._events.dispatch_pending()
        return attempt
