from datetime import UTC, datetime, timedelta
from typing import Any

from agent_zero.attempts.models import Attempt, AttemptOutcome, AttemptStatus
from agent_zero.llm.models import CallKind, CallOrigin, CallOutcome
from agent_zero.llm.schemas import CallRecord, CallScope, CallUsage
from agent_zero.routing.models import Route
from agent_zero.sessions.models import ArenaSession

T0 = datetime(2026, 10, 24, 15, 0, tzinfo=UTC)


def at(seconds: float) -> datetime:
    return T0 + timedelta(seconds=seconds)


def session(
    session_id: str, alias: str, route: Route = Route.PROTECTED, created: float = 0
) -> ArenaSession:
    return ArenaSession(
        id=session_id, alias=alias, customer_id="cust-1", route=route, created_at=at(created)
    )


def attempt(  # noqa: PLR0913
    attempt_id: str,
    session_id: str,
    *,
    seconds: float,
    outcome: AttemptOutcome | None = AttemptOutcome.NOT_ACHIEVED,
    route: Route = Route.PROTECTED,
    status: AttemptStatus = AttemptStatus.EVALUATED,
    campaign_id: str | None = None,
    violated: list[str] | None = None,
    reply: str = "Respuesta.",
) -> Attempt:
    assessment: dict[str, Any] = {
        "verdicts": [{"objective_id": o, "violated": True} for o in violated or []]
    }
    return Attempt(
        id=attempt_id,
        session_id=session_id,
        origin="audience",
        campaign_id=campaign_id,
        policy_version=0,
        route=route,
        run_id=f"run-{attempt_id}",
        idempotency_key=f"key-{attempt_id}",
        messages=["Mensaje."],
        customer_id="cust-1",
        status=status,
        outcome=outcome,
        reply=reply,
        assessment=assessment,
        defense_processed=False,
        created_at=at(seconds),
        updated_at=at(seconds),
    )


def call(
    role: str,
    *,
    tokens: int | None,
    origin: CallOrigin = CallOrigin.LIVE,
    campaign_id: str | None = None,
    session_id: str | None = None,
) -> CallRecord:
    usage = (
        None
        if tokens is None
        else CallUsage(input_tokens=tokens // 2, output_tokens=tokens - tokens // 2)
    )
    return CallRecord(
        call_id=f"call-{role}-{tokens}-{campaign_id}-{session_id}",
        at=T0,
        role=role,
        model_id="modelo-x",
        kind=CallKind.STREAM,
        origin=origin,
        outcome=CallOutcome.OK,
        latency_ms=1.0,
        usage=usage,
        scope=CallScope(campaign_id=campaign_id, session_id=session_id),
    )
