import json
from typing import Any

from pydantic import TypeAdapter, ValidationError

from agent_zero.agent_gateway.business_policy import CallContext
from agent_zero.events.event_store import EventStore
from agent_zero.events.models import EventType
from agent_zero.events.schemas import EventDraft, TraceEvent
from agent_zero.shared.clock import utc_now
from agent_zero.victim.trace_schemas import (
    CompletedData,
    DeniedData,
    FailedData,
    ProposedData,
    ToolEffect,
    TraceData,
)

_EFFECT: TypeAdapter[ToolEffect] = TypeAdapter(ToolEffect)


def _as_object(output: Any) -> dict[str, Any] | None:
    try:
        parsed = json.loads(output) if isinstance(output, str) else output
    except ValueError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _as_effect(effect: Any) -> ToolEffect | None:
    try:
        return _EFFECT.validate_python(effect) if effect is not None else None
    except ValidationError:
        return None


def trace_data(kind: str, context: CallContext, tool: str, data: dict[str, Any]) -> TraceData:
    common: dict[str, Any] = {
        "tool": tool,
        "arguments": data.get("arguments", {}),
        "environment": context.environment,
        "session_customer_id": context.session_customer_id,
        "operation_id": context.operation_id,
        "provenance": dict(context.provenance),
    }
    if kind == EventType.TOOL_COMPLETED:
        return CompletedData(
            **common, output=_as_object(data.get("output")), effect=_as_effect(data.get("effect"))
        )
    if kind == EventType.TOOL_DENIED:
        return DeniedData(
            **common,
            stage=data["stage"],
            reason=data["reason"],
            validator=data.get("validator"),
            detail=data.get("detail"),
            data_region=data.get("data_region"),
        )
    if kind == EventType.TOOL_FAILED:
        return FailedData(**common, error=data["error"])
    return ProposedData(**common)


class TraceObserver:
    def __init__(self, events: EventStore) -> None:
        self._events = events
        self._validation: dict[str, list[TraceEvent]] = {}

    def capture(self, key: str) -> list[TraceEvent]:
        events: list[TraceEvent] = []
        self._validation[key] = events
        return events

    def release(self, key: str) -> None:
        self._validation.pop(key, None)

    async def record(
        self, kind: str, context: CallContext, tool: str, data: dict[str, Any]
    ) -> None:
        draft = EventDraft(
            type=EventType(kind),
            attempt_id=context.attempt_id,
            session_id=context.session_id,
            policy_version=context.policy_version,
            data=trace_data(kind, context, tool, data).model_dump(mode="json"),
        )
        if context.environment == "validation":
            captured = self._validation[context.environment_id]
            captured.append(
                TraceEvent(id=len(captured) + 1, timestamp=utc_now(), **draft.model_dump())
            )
        else:
            await self._events.emit(draft, dedup_key=f"{context.operation_id}:{kind}")
            await self._events.public(
                EventType(kind),
                context.policy_version,
                status=kind,
                dedup_key=f"public:{context.operation_id}:{kind}",
            )
