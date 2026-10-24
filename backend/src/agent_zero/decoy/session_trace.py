from agent_zero.attempts.models import Attempt
from agent_zero.decoy.models import SessionTrace
from agent_zero.events.models import EventType
from agent_zero.events.schemas import TraceEvent
from agent_zero.routing.models import Route
from agent_zero.victim.honeytool_schemas import HONEYTOOL_MODELS

CREDENTIAL_TOOL = "get_service_credentials"
MIN_ATTEMPTS_TO_RETAIN = 2


def _issued_at(after: list[TraceEvent]) -> TraceEvent | None:
    return next(
        (
            event
            for event in after
            if event.type is EventType.TOOL_COMPLETED and event.data.get("tool") == CREDENTIAL_TOOL
        ),
        None,
    )


def _reused(token: str, attempts: list[Attempt], issued: TraceEvent | None) -> bool:
    if issued is None:
        return False
    needle = token.casefold()
    return any(
        attempt.created_at > issued.timestamp
        and any(needle in message.casefold() for message in attempt.messages)
        for attempt in attempts
    )


def build_trace(
    *,
    session_id: str,
    alias: str,
    events: list[TraceEvent],
    attempts: list[Attempt],
    token: str,
) -> SessionTrace | None:
    route = next((event for event in events if event.type is EventType.ROUTE_CHANGED), None)
    if route is None:
        return None
    after = [event for event in events if event.id > route.id]
    contained = [attempt for attempt in attempts if attempt.route is Route.HONEYPOT]
    moments = [event.timestamp for event in after] + [attempt.updated_at for attempt in contained]
    last = max(moments, default=route.timestamp)
    steps = sum(1 for event in after if event.type is EventType.TOOL_PROPOSED)
    touched = sorted(
        {
            str(event.data["tool"])
            for event in after
            if event.type is EventType.TOOL_COMPLETED and event.data.get("tool") in HONEYTOOL_MODELS
        }
    )
    issued = _issued_at(after)
    reused = _reused(token, attempts, issued)
    return SessionTrace(
        session_id=session_id,
        alias=alias,
        reason=str(route.data.get("reason", "")),
        retained_seconds=round(max((last - route.timestamp).total_seconds(), 0.0), 3),
        post_diversion_steps=steps,
        post_diversion_attempts=len(contained),
        honeytools_touched=touched,
        credential_issued=issued is not None,
        token_reused=reused,
        retained=steps >= 1 or len(contained) >= MIN_ATTEMPTS_TO_RETAIN,
        bait_taken=bool(touched),
        deceived=reused,
    )
