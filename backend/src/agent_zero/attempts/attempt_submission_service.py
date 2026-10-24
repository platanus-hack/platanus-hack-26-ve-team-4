import asyncio
from datetime import timedelta
from typing import Literal

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from agent_zero.arena.models import ArenaState
from agent_zero.attempts.models import Attempt, AttemptStatus
from agent_zero.attempts.repository import AttemptRepository
from agent_zero.attempts.schemas import AttemptCreate
from agent_zero.events.event_store import EventStore
from agent_zero.events.models import EventType
from agent_zero.events.schemas import EventDraft
from agent_zero.fleet.fleet_builder import Fleet
from agent_zero.policies.policy_service import PolicyService
from agent_zero.routing.route_decision_service import RouteDecisionService
from agent_zero.runtime.run_enqueue_service import RunEnqueueService
from agent_zero.runtime.schemas import RunCreate
from agent_zero.sessions.session_query_service import query_session
from agent_zero.shared.ids import new_id
from agent_zero.victim.arena_manifest import ARENA_HANDLER, ARENA_VERSION


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
            repository = AttemptRepository(db)
            existing = await repository.by_key(session_id, payload.idempotency_key)
            if existing is not None:
                return existing
            session = await query_session(db, session_id)
            if session is None:
                raise HTTPException(401, "Sesión no disponible.")
            state = await db.get(ArenaState, 1)
            if state is None or not state.accepting:
                raise HTTPException(409, "Las entradas de la ronda están cerradas.")
            settings = self._fleet.settings
            if (
                await repository.in_flight() >= settings.arena_queue_limit
                or await repository.in_flight(session_id) >= settings.arena_session_queue_limit
            ):
                raise HTTPException(429, "La cola está llena; espera el resultado anterior.")
            now = self._fleet.clock()
            if (
                await repository.recent_count(session_id, now - timedelta(minutes=1))
                >= settings.arena_attempts_per_minute
            ):
                raise HTTPException(429, "Alcanzaste el límite de intentos por minuto.")
            route = await self._routing.decide(session, payload.turns)
            version = await self._policies.active_version()
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
            try:
                await db.commit()
            except IntegrityError:
                await db.rollback()
                duplicate = await repository.by_key(session_id, payload.idempotency_key)
                if duplicate is None:
                    raise
                return duplicate
        await self._events.emit(
            EventDraft(
                type=EventType.ATTEMPT_QUEUED,
                attempt_id=attempt.id,
                session_id=session_id,
                policy_version=version,
                data={"origin": origin},
            )
        )
        await self._events.public(EventType.ATTEMPT_QUEUED, version, status="queued")
        return attempt
