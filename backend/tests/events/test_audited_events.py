from agent_zero.events.audited_events import AuditedEvents, audited_events
from agent_zero.telemetry.audit_log import AuditLog
from agent_zero.telemetry.audit_schemas import AuditDecision, AuditEvent


def _event(actor: str, event_id: str) -> AuditEvent:
    return AuditEvent(
        actor=actor,
        action="attempt.queued",
        resource="arena",
        decision=AuditDecision.INFO,
        attributes={"event_id": event_id, "event_hash": f"h-{event_id}"},
    )


def test_index_only_reads_new_entries_and_ignores_other_actors() -> None:
    audit = AuditLog.in_memory()
    index = AuditedEvents()
    audit.append(_event("arena", "e1"))
    audit.append(_event("gateway", "e2"))
    assert index.refresh(audit) == {("e1", "h-e1")}
    audit.append(_event("arena", "e3"))
    assert index.refresh(audit) == {("e1", "h-e1"), ("e3", "h-e3")}


def test_index_rebuilds_when_the_log_shrinks() -> None:
    first, second = AuditLog.in_memory(), AuditLog.in_memory()
    first.append(_event("arena", "e1"))
    first.append(_event("arena", "e2"))
    second.append(_event("arena", "e9"))
    index = AuditedEvents()
    index.refresh(first)
    assert index.refresh(second) == {("e9", "h-e9")}


def test_each_log_keeps_its_own_index() -> None:
    first, second = AuditLog.in_memory(), AuditLog.in_memory()
    first.append(_event("arena", "a"))
    second.append(_event("arena", "b"))
    assert audited_events(first) == {("a", "h-a")}
    assert audited_events(second) == {("b", "h-b")}
