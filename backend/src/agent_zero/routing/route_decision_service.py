from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.arena.transactions import serialize_write
from agent_zero.armor.models import Surface
from agent_zero.attempts.repository import AttemptRepository
from agent_zero.events.event_store import EventStore
from agent_zero.events.models import EventType
from agent_zero.events.schemas import EventDraft
from agent_zero.fleet.fleet_builder import Fleet
from agent_zero.routing.models import Route
from agent_zero.routing.session_risk_reader import session_risk
from agent_zero.sessions.models import ArenaSession


class RouteDecisionService:
    def __init__(self, fleet: Fleet, events: EventStore) -> None:
        self._fleet = fleet
        self._events = events

    async def decide(
        self, session: ArenaSession, messages: list[str], db: AsyncSession | None = None
    ) -> Route:
        if db is None:
            async with self._fleet.database.sessions() as own_db:
                await serialize_write(own_db)
                stored = await own_db.get(ArenaSession, session.id)
                if stored is None:
                    raise ValueError("Sesión no disponible.")
                route = await self.decide(stored, messages, own_db)
                await own_db.commit()
            await self._events.dispatch_pending()
            return route
        if session.route is Route.HONEYPOT:
            return Route.HONEYPOT
        suspicious = any(
            self._fleet.armor.screen(message, Surface.USER_INPUT).blocked for message in messages
        )
        prior_violation = await AttemptRepository(db).needs_diversion(session.id)
        settings = self._fleet.settings
        risky = (
            await session_risk(self._events, session, settings.routing_risk_window_seconds, db)
            >= settings.routing_risk_threshold
        )
        if not (suspicious or prior_violation or risky):
            return Route.PROTECTED
        session.route = Route.HONEYPOT
        await self._events.stage(
            db,
            EventDraft(
                type=EventType.ROUTE_CHANGED,
                session_id=session.id,
                data={
                    "route": "honeypot",
                    "reason": "armor"
                    if suspicious
                    else "confirmed_violation"
                    if prior_violation
                    else "risk_score",
                },
            ),
            dedup_key=f"{session.id}:diverted",
        )
        return Route.HONEYPOT
