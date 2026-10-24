import hashlib

from sqlalchemy import select

from agent_zero.arena.transactions import serialize_write
from agent_zero.events.broker import EventBroker
from agent_zero.events.models import EventDelivery, EventRecord
from agent_zero.events.schemas import TraceEvent
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


async def deliver_pending(fleet: Fleet, broker: EventBroker) -> int:
    """Publish committed events; replay after a crash retains the original event ID.

    The database reservation serializes dispatchers. Audit entries are addressed by
    event ID/hash, so a crash after append but before acknowledgment does not append
    another audit entry. Subscribers can always recover from the durable event log.
    """
    async with fleet.database.sessions() as db:
        await serialize_write(db)
        pending = list(
            await db.execute(
                select(EventDelivery, EventRecord)
                .join(EventRecord, EventRecord.id == EventDelivery.event_id)
                .where(EventDelivery.delivered_at.is_(None))
                .order_by(EventRecord.id)
                .limit(100)
            )
        )
        if not pending:
            return 0
        audited = {
            (entry.attributes.get("event_id"), entry.attributes.get("event_hash"))
            for entry in fleet.audit.entries()
            if entry.actor == "arena"
        }
        for delivery, row in pending:
            event = to_trace(row)
            digest = hashlib.sha256(event.model_dump_json().encode()).hexdigest()
            if (event.id, digest) not in audited:
                fleet.audit.append(
                    AuditEvent(
                        actor="arena",
                        action=event.type.value,
                        resource=event.attempt_id or "arena",
                        decision=AuditDecision.INFO,
                        attributes={
                            "event_id": event.id,
                            "event_hash": digest,
                            "policy_version": event.policy_version,
                            "session_id": event.session_id,
                        },
                    )
                )
            broker.publish_event(event)
            delivery.delivered_at = fleet.clock()
        await db.commit()
        return len(pending)
