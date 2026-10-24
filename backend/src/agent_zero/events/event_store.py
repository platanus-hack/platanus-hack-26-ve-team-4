import hashlib
from typing import Any

from sqlalchemy import select

from agent_zero.events.broker import EventBroker
from agent_zero.events.models import EventRecord, EventType, Visibility
from agent_zero.events.public_projection import PUBLIC_FIELDS
from agent_zero.events.schemas import EventDraft, TraceEvent
from agent_zero.fleet.fleet_builder import Fleet
from agent_zero.telemetry.audit_schemas import AuditDecision, AuditEvent


def to_trace(row: EventRecord) -> TraceEvent:
    return TraceEvent(
        id=row.id,
        type=row.type,
        visibility=row.visibility,
        attempt_id=row.attempt_id,
        session_id=row.session_id,
        policy_version=row.policy_version,
        data=row.data,
        timestamp=row.timestamp,
    )


class EventStore:
    def __init__(self, fleet: Fleet, broker: EventBroker) -> None:
        self._fleet = fleet
        self._broker = broker

    async def restore(self) -> None:
        self._broker.set_history_source(self.public_after)
        async with self._fleet.database.sessions() as db:
            rows = await db.scalars(select(EventRecord).order_by(EventRecord.id.desc()).limit(500))
            for row in reversed(list(rows)):
                self._broker.publish_event(to_trace(row))

    async def public_after(self, after_id: int) -> list[TraceEvent]:
        async with self._fleet.database.sessions() as db:
            rows = await db.scalars(
                select(EventRecord)
                .where(
                    EventRecord.id > after_id,
                    EventRecord.visibility == Visibility.PUBLIC,
                )
                .order_by(EventRecord.id)
            )
            return [to_trace(row) for row in rows]

    async def emit(self, draft: EventDraft, *, dedup_key: str | None = None) -> TraceEvent:
        # Redact values without changing field names, identifiers or the public allowlist.
        data = self._sanitize(draft.data)
        async with self._fleet.database.sessions() as db:
            if dedup_key is not None:
                previous = await db.scalar(
                    select(EventRecord).where(EventRecord.dedup_key == dedup_key)
                )
                if previous is not None:
                    return to_trace(previous)
            row = EventRecord(
                **draft.model_dump(exclude={"data"}),
                data=data,
                timestamp=self._fleet.clock(),
                dedup_key=dedup_key,
            )
            db.add(row)
            await db.commit()
            event = to_trace(row)
        self._fleet.audit.append(
            AuditEvent(
                actor="arena",
                action=draft.type.value,
                resource=draft.attempt_id or "arena",
                decision=AuditDecision.INFO,
                attributes={
                    "event_id": event.id,
                    "event_hash": hashlib.sha256(event.model_dump_json().encode()).hexdigest(),
                    "policy_version": draft.policy_version,
                    "session_id": draft.session_id,
                },
            )
        )
        self._broker.publish_event(event)
        return event

    def _sanitize(self, value: dict[str, Any]) -> dict[str, Any]:
        return {key: self._redact_value(item) for key, item in value.items()}

    def _redact_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {key: self._redact_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._redact_value(item) for item in value]
        if isinstance(value, str):
            return self._fleet.armor.redact_pii(value)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            redacted = self._fleet.armor.redact_pii(str(value))
            return redacted if redacted != str(value) else value
        return value

    async def for_attempt(self, attempt_id: str) -> list[TraceEvent]:
        async with self._fleet.database.sessions() as db:
            rows = await db.scalars(
                select(EventRecord)
                .where(
                    EventRecord.attempt_id == attempt_id,
                    EventRecord.visibility == Visibility.OPERATOR,
                )
                .order_by(EventRecord.id)
            )
            return [to_trace(row) for row in rows]

    async def public(
        self, kind: EventType, policy_version: int, *, dedup_key: str | None = None, **data: Any
    ) -> None:
        await self.emit(
            EventDraft(
                type=kind,
                visibility=Visibility.PUBLIC,
                policy_version=policy_version,
                data={key: value for key, value in data.items() if key in PUBLIC_FIELDS},
            ),
            dedup_key=dedup_key,
        )

    async def consecutive_denials(self, session_id: str) -> bool:
        async with self._fleet.database.sessions() as db:
            kinds = list(
                await db.scalars(
                    select(EventRecord.type)
                    .where(
                        EventRecord.session_id == session_id,
                        EventRecord.visibility == Visibility.OPERATOR,
                        EventRecord.type.in_([EventType.TOOL_DENIED, EventType.TOOL_COMPLETED]),
                    )
                    .order_by(EventRecord.id.desc())
                    .limit(3)
                )
            )
            return len(kinds) == 3 and all(kind is EventType.TOOL_DENIED for kind in kinds)
