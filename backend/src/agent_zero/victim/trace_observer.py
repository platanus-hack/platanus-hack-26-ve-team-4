from typing import Any

from agent_zero.agent_gateway.business_policy import CallContext
from agent_zero.events.event_store import EventStore
from agent_zero.events.models import EventType
from agent_zero.events.schemas import EventDraft, TraceEvent
from agent_zero.shared.clock import utc_now


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
            data=data
            | {
                "tool": tool,
                "environment": context.environment,
                "session_customer_id": context.session_customer_id,
                "operation_id": context.operation_id,
            }
            | ({"provenance": dict(context.provenance)} if context.provenance else {}),
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
