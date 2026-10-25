from weakref import WeakKeyDictionary

from agent_zero.telemetry.audit_log import AuditLog

AuditedKey = tuple[object, object]


class AuditedEvents:
    def __init__(self) -> None:
        self._seen: set[AuditedKey] = set()
        self._count = 0

    def refresh(self, audit: AuditLog) -> set[AuditedKey]:
        entries = audit.entries()
        if len(entries) < self._count:
            self._seen, self._count = set(), 0
        for entry in entries[self._count :]:
            if entry.actor == "arena":
                attributes = entry.attributes
                self._seen.add((attributes.get("event_id"), attributes.get("event_hash")))
        self._count = len(entries)
        return self._seen


_INDEXES: WeakKeyDictionary[AuditLog, AuditedEvents] = WeakKeyDictionary()


def audited_events(audit: AuditLog) -> set[AuditedKey]:
    index = _INDEXES.get(audit)
    if index is None:
        index = _INDEXES[audit] = AuditedEvents()
    return index.refresh(audit)
