from datetime import UTC, datetime

from agent_zero.llm.models import CallKind, CallOrigin, CallOutcome
from agent_zero.llm.schemas import CallCost, CallRecord, CallUsage


def call_record(
    role: str = "prober",
    outcome: CallOutcome = CallOutcome.OK,
    latency_ms: float = 10.0,
    usage: CallUsage | None = None,
    cost: CallCost | None = None,
) -> CallRecord:
    return CallRecord(
        call_id=f"call-{role}-{latency_ms}",
        at=datetime(2026, 10, 24, tzinfo=UTC),
        role=role,
        model_id="claude-haiku-5-5",
        kind=CallKind.STREAM,
        origin=CallOrigin.SIMULATED,
        outcome=outcome,
        latency_ms=latency_ms,
        usage=usage,
        cost=cost,
    )
