import secrets
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from opentelemetry import trace

from agent_zero.config import Settings
from agent_zero.telemetry.audit_anchor import AnchorStore, FileAnchor, MemoryAnchor, sign_anchor
from agent_zero.telemetry.audit_hashing import compute_hash, derive_audit_key
from agent_zero.telemetry.audit_journal import AuditJournal
from agent_zero.telemetry.audit_schemas import (
    GENESIS_HASH,
    AuditEntry,
    AuditEvent,
    AuditVerification,
)
from agent_zero.telemetry.audit_store import AuditStore, FileAuditStore, MemoryAuditStore
from agent_zero.telemetry.audit_verifier import verify_lines
from agent_zero.telemetry.errors import AuditIntegrityError

Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _active_ids() -> tuple[str | None, str | None]:
    context = trace.get_current_span().get_span_context()
    if not context.is_valid:
        return None, None
    return format(context.trace_id, "032x"), format(context.span_id, "016x")


class AuditLog:
    def __init__(
        self, store: AuditStore, key: bytes, anchor: AnchorStore, clock: Clock = _utc_now
    ) -> None:
        self._store = store
        self._key = key
        self._anchor = anchor
        self._clock = clock
        self._lock = threading.Lock()
        self._verified: list[str] = []
        self._journal = (
            AuditJournal(store, anchor, key) if isinstance(store, FileAuditStore) else None
        )

    @classmethod
    def for_file(cls, path: Path, key: bytes, clock: Clock = _utc_now) -> "AuditLog":
        anchor = FileAnchor(path.with_suffix(path.suffix + ".anchor"))
        return cls(FileAuditStore(path), key, anchor, clock)

    @classmethod
    def from_settings(cls, settings: Settings, clock: Clock = _utc_now) -> "AuditLog":
        return cls.for_file(settings.audit_log_path, derive_audit_key(settings), clock)

    @classmethod
    def in_memory(cls, clock: Clock = _utc_now, key: bytes | None = None) -> "AuditLog":
        return cls(MemoryAuditStore(), key or secrets.token_bytes(32), MemoryAnchor(), clock)

    def append(self, event: AuditEvent) -> AuditEntry:
        trace_id, span_id = _active_ids()
        with self._lock, self._store.locked():
            if self._journal is not None:
                self._journal.recover()
            lines = self._store.read_lines()
            prev_hash = self._verify_for_append(lines)
            draft = AuditEntry(
                sequence=len(lines),
                at=self._clock(),
                actor=event.actor,
                action=event.action,
                resource=event.resource,
                decision=event.decision,
                reason=event.reason,
                trace_id=trace_id,
                span_id=span_id,
                attributes=dict(event.attributes),
                prev_hash=prev_hash,
                hash="",
            )
            entry = draft.model_copy(update={"hash": compute_hash(draft, self._key)})
            if self._journal is not None:
                self._journal.prepare(entry.model_dump_json())
            line = entry.model_dump_json()
            self._store.append_line(line)
            self._anchor.write(sign_anchor(self._key, len(lines) + 1, entry.hash))
            self._verified = [*lines, line]
            if self._journal is not None:
                self._journal.clear()
            return entry

    def _verify_for_append(self, lines: list[str]) -> str:
        known = len(self._verified)
        start, prev_hash = 0, GENESIS_HASH
        if known and lines[:known] == self._verified:
            start, prev_hash = known, AuditEntry.model_validate_json(lines[known - 1]).hash
        verification = verify_lines(lines, self._key, self._anchor, start, prev_hash)
        if not verification.ok:
            self._verified = []
            raise AuditIntegrityError(verification.detail)
        if lines:
            return AuditEntry.model_validate_json(lines[-1]).hash
        return GENESIS_HASH

    def entries(self) -> list[AuditEntry]:
        with self._lock, self._store.locked():
            if self._journal is not None:
                self._journal.recover()
            return [AuditEntry.model_validate_json(line) for line in self._store.read_lines()]

    def verify(self) -> AuditVerification:
        with self._lock, self._store.locked():
            if self._journal is not None:
                try:
                    self._journal.recover()
                except AuditIntegrityError as error:
                    return AuditVerification(
                        ok=False, entries=len(self._store.read_lines()), detail=str(error)
                    )
            return verify_lines(self._store.read_lines(), self._key, self._anchor)
