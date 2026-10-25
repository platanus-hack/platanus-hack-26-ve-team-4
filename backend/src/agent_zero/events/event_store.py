import re
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_zero.arena.round_models import RoundMetadata
from agent_zero.arena.transactions import serialize_write
from agent_zero.events.broker import EventBroker
from agent_zero.events.event_delivery import deliver_pending, to_trace
from agent_zero.events.models import EventDelivery, EventRecord, EventType, Visibility
from agent_zero.events.public_projection import PUBLIC_FIELDS
from agent_zero.events.schemas import EventDraft, TraceEvent
from agent_zero.fleet.fleet_builder import Fleet

# Identifiers minted by `shared.ids.new_id`. Their hex part can look like a phone number
# ("finding-929410922ffb"), so redacting them would break links between events and rows.
SERVER_ID = re.compile(r"[a-z]+(?:-[a-z]+)*-[0-9a-f]{12}")


def is_identifier_key(key: str) -> bool:
    return key == "id" or key.endswith(("_id", "_ids"))


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
        await self.dispatch_pending()

    async def dispatch_pending(self) -> int:
        return await deliver_pending(self._fleet, self._broker)

    async def public_after(self, after_id: int) -> list[TraceEvent]:
        async with self._fleet.database.sessions() as db:
            metadata = await db.get(RoundMetadata, 1)
            first_id = metadata.first_event_id if metadata is not None else 0
            rows = await db.scalars(
                select(EventRecord)
                .where(
                    EventRecord.id > after_id,
                    EventRecord.id >= first_id,
                    EventRecord.visibility == Visibility.PUBLIC,
                )
                .order_by(EventRecord.id)
            )
            return [to_trace(row) for row in rows]

    async def stage(
        self, db: AsyncSession, draft: EventDraft, *, dedup_key: str | None = None
    ) -> TraceEvent:
        """Persist an event in the caller's transaction, together with its domain change.

        The caller must reserve the writer before any reads. No audit or subscriber
        sees the draft until that transaction commits and the dispatcher publishes it.
        """
        if dedup_key is not None:
            previous = await db.scalar(
                select(EventRecord).where(EventRecord.dedup_key == dedup_key)
            )
            if previous is not None:
                return to_trace(previous)
        row = EventRecord(
            **draft.model_dump(exclude={"data"}),
            data=self._sanitize(draft.data),
            timestamp=self._fleet.clock(),
            dedup_key=dedup_key,
        )
        db.add(row)
        await db.flush()
        db.add(EventDelivery(event_id=row.id))
        await db.flush()
        return to_trace(row)

    async def emit(self, draft: EventDraft, *, dedup_key: str | None = None) -> TraceEvent:
        async with self._fleet.database.sessions() as db:
            await serialize_write(db)
            event = await self.stage(db, draft, dedup_key=dedup_key)
            await db.commit()
        await self.dispatch_pending()
        return event

    async def stage_public(
        self,
        db: AsyncSession,
        kind: EventType,
        policy_version: int,
        *,
        dedup_key: str | None = None,
        **data: Any,
    ) -> None:
        await self.stage(
            db,
            EventDraft(
                type=kind,
                visibility=Visibility.PUBLIC,
                policy_version=policy_version,
                data={key: value for key, value in data.items() if key in PUBLIC_FIELDS},
            ),
            dedup_key=dedup_key,
        )

    async def public(
        self, kind: EventType, policy_version: int, *, dedup_key: str | None = None, **data: Any
    ) -> None:
        async with self._fleet.database.sessions() as db:
            await serialize_write(db)
            await self.stage_public(db, kind, policy_version, dedup_key=dedup_key, **data)
            await db.commit()
        await self.dispatch_pending()

    def _sanitize(self, value: dict[str, Any]) -> dict[str, Any]:
        return {key: self._redact_value(item, key) for key, item in value.items()}

    def _redact_value(self, value: Any, key: str | None = None) -> Any:
        if isinstance(value, dict):
            return {name: self._redact_value(item, name) for name, item in value.items()}
        if isinstance(value, list):
            return [self._redact_value(item, key) for item in value]
        if isinstance(value, str):
            # Only server-minted ids under id fields skip redaction: an id field may also
            # carry model-proposed text (a tool's order_id), which is still redacted.
            if key is not None and is_identifier_key(key) and SERVER_ID.fullmatch(value):
                return value
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

    async def tool_outcomes(
        self, session_id: str, since: datetime, db: AsyncSession
    ) -> list[tuple[EventType, dict[str, Any]]]:
        rows = await db.execute(
            select(EventRecord.type, EventRecord.data)
            .where(
                EventRecord.session_id == session_id,
                EventRecord.visibility == Visibility.OPERATOR,
                EventRecord.type.in_([EventType.TOOL_DENIED, EventType.TOOL_COMPLETED]),
                EventRecord.timestamp >= since,
            )
            .order_by(EventRecord.id)
        )
        return [(kind, dict(data)) for kind, data in rows]
