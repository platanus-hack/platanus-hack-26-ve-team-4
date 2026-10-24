from agent_zero.armor.models import Surface
from agent_zero.attempts.attempt_query_service import AttemptQueryService
from agent_zero.events.event_store import EventStore
from agent_zero.events.models import EventType
from agent_zero.events.schemas import EventDraft
from agent_zero.fleet.fleet_builder import Fleet
from agent_zero.routing.models import Route
from agent_zero.sessions.models import ArenaSession
from agent_zero.sessions.session_query_service import divert_session


class RouteDecisionService:
    def __init__(self, fleet: Fleet, events: EventStore) -> None:
        self._fleet = fleet
        self._events = events

    async def decide(self, session: ArenaSession, messages: list[str]) -> Route:
        if session.route is Route.HONEYPOT:
            return Route.HONEYPOT
        suspicious = any(
            self._fleet.armor.screen(message, Surface.USER_INPUT).blocked for message in messages
        )
        prior_violation = await AttemptQueryService(self._fleet.database).needs_diversion(
            session.id
        )
        repeated_denials = await self._events.consecutive_denials(session.id)
        async with self._fleet.database.sessions() as db:
            if not (suspicious or prior_violation or repeated_denials):
                return Route.PROTECTED
            await divert_session(db, session.id)
        await self._events.emit(
            EventDraft(
                type=EventType.ROUTE_CHANGED,
                session_id=session.id,
                data={
                    "route": "honeypot",
                    "reason": "armor"
                    if suspicious
                    else "confirmed_violation"
                    if prior_violation
                    else "repeated_denials",
                },
            )
        )
        return Route.HONEYPOT
