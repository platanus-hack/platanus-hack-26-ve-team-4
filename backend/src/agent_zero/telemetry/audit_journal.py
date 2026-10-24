from pydantic import ValidationError

from agent_zero.telemetry.audit_anchor import AnchorStore, MemoryAnchor, sign_anchor
from agent_zero.telemetry.audit_files import atomic_write, sync_directory
from agent_zero.telemetry.audit_hashing import compute_hash
from agent_zero.telemetry.audit_schemas import AuditEntry
from agent_zero.telemetry.audit_store import FileAuditStore
from agent_zero.telemetry.audit_verifier import verify_lines
from agent_zero.telemetry.errors import AuditIntegrityError


class AuditJournal:
    """A signed pending entry makes line+anchor publication recoverable after a crash.

    The caller holds the audit file's OS lock throughout prepare/write/anchor/clear.
    Recovery only completes this authenticated append; unrelated truncation,
    modifications, missing anchors and forged tails remain integrity failures.
    """

    def __init__(self, store: FileAuditStore, anchor: AnchorStore, key: bytes) -> None:
        self._store = store
        self._anchor = anchor
        self._key = key
        self._path = store.path.with_suffix(store.path.suffix + ".pending")

    def prepare(self, line: str) -> None:
        atomic_write(self._path, line + "\n")

    def clear(self) -> None:
        self._path.unlink(missing_ok=True)
        sync_directory(self._path.parent)

    def recover(self) -> None:
        if not self._path.exists():
            return
        pending = self._path.read_text(encoding="utf-8").strip()
        try:
            entry = AuditEntry.model_validate_json(pending)
        except ValidationError as error:
            raise AuditIntegrityError("La entrada pendiente de auditoría es ilegible.") from error
        if compute_hash(entry, self._key) != entry.hash:
            raise AuditIntegrityError("La firma de la entrada pendiente de auditoría no coincide.")
        lines = self._store.read_lines()
        if len(lines) not in {entry.sequence, entry.sequence + 1}:
            raise AuditIntegrityError("La entrada pendiente no corresponde al final del registro.")
        if (
            len(lines) == entry.sequence + 1
            and lines[-1] == pending
            and verify_lines(lines, self._key, self._anchor).ok
        ):
            self.clear()
            return
        base = lines[: entry.sequence]
        if not verify_lines(base, self._key, self._anchor).ok:
            raise AuditIntegrityError("La entrada pendiente no continúa un registro verificado.")
        candidate = [*base, pending]
        # Check the signed entry's sequence and predecessor before touching the log.
        from_anchor = MemoryAnchor()
        from_anchor.write(sign_anchor(self._key, len(candidate), entry.hash))
        if not verify_lines(candidate, self._key, from_anchor).ok:
            raise AuditIntegrityError("La entrada pendiente no continúa la cadena firmada.")
        if len(lines) == entry.sequence:
            self._store.append_line(pending)
        elif lines[-1] != pending:
            raw = self._store.path.read_bytes()
            if raw.endswith(b"\n") or not pending.startswith(lines[-1]):
                raise AuditIntegrityError(
                    "El final del registro no coincide con la escritura pendiente."
                )
            atomic_write(self._store.path, "\n".join(candidate) + "\n")
        self._anchor.write(sign_anchor(self._key, len(candidate), entry.hash))
        self.clear()
