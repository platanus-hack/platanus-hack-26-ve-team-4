import multiprocessing
from pathlib import Path

import pytest

from agent_zero.telemetry.audit_anchor import FileAnchor
from agent_zero.telemetry.audit_log import AuditLog
from agent_zero.telemetry.audit_schemas import AuditDecision, AuditEvent
from agent_zero.telemetry.audit_store import FileAuditStore
from agent_zero.telemetry.errors import AuditIntegrityError

KEY = b"durable-audit-test-key"


def _event(resource: str) -> AuditEvent:
    return AuditEvent(
        actor="test", action="concurrent", resource=resource, decision=AuditDecision.INFO
    )


def _write_from_process(path: str, participant: int, count: int) -> None:
    log = AuditLog.for_file(Path(path), KEY)
    for index in range(count):
        log.append(_event(f"{participant}:{index}"))


def test_independent_processes_share_one_atomic_hash_chain_and_anchor(tmp_path: Path) -> None:
    path = tmp_path / "shared" / "audit.jsonl"
    context = multiprocessing.get_context("spawn")
    processes = [
        context.Process(target=_write_from_process, args=(str(path), index, 15))
        for index in range(5)
    ]
    for process in processes:
        process.start()
    try:
        for process in processes:
            process.join(timeout=30)
        assert [process.exitcode for process in processes] == [0] * 5
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
    log = AuditLog.for_file(path, KEY)
    assert log.verify().ok
    entries = log.entries()
    assert [entry.sequence for entry in entries] == list(range(75))
    assert len({entry.resource for entry in entries}) == 75
    assert not path.with_suffix(".jsonl.pending").exists()


def test_reopen_recovers_signed_append_after_anchor_write_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "audit.jsonl"
    log = AuditLog.for_file(path, KEY)
    log.append(_event("before"))
    with monkeypatch.context() as patch:

        def failed_anchor(self: FileAnchor, value: str) -> None:
            raise OSError("disk failure on anchor")

        patch.setattr(FileAnchor, "write", failed_anchor)
        with pytest.raises(OSError, match="disk failure"):
            log.append(_event("durable-pending"))
    assert path.with_suffix(".jsonl.pending").exists()
    reopened = AuditLog.for_file(path, KEY)
    assert reopened.verify().ok
    assert [entry.resource for entry in reopened.entries()] == ["before", "durable-pending"]
    reopened.append(_event("after"))
    assert reopened.verify().ok
    assert len(reopened.entries()) == 3
    assert not path.with_suffix(".jsonl.pending").exists()


def test_reopen_recovers_prepared_entry_when_append_did_not_start(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "audit.jsonl"
    log = AuditLog.for_file(path, KEY)
    with monkeypatch.context() as patch:

        def failed_append(self: FileAuditStore, line: str) -> None:
            raise OSError("disk failure before append")

        patch.setattr(FileAuditStore, "append_line", failed_append)
        with pytest.raises(OSError, match="before append"):
            log.append(_event("prepared"))
    reopened = AuditLog.for_file(path, KEY)
    assert [entry.resource for entry in reopened.entries()] == ["prepared"]
    assert reopened.verify().ok


def test_reopen_completes_only_matching_partial_tail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "audit.jsonl"
    log = AuditLog.for_file(path, KEY)
    log.append(_event("before"))
    with monkeypatch.context() as patch:

        def torn_append(self: FileAuditStore, line: str) -> None:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line[: len(line) // 2])
                handle.flush()
            raise OSError("torn write")

        patch.setattr(FileAuditStore, "append_line", torn_append)
        with pytest.raises(OSError, match="torn write"):
            log.append(_event("partial"))
    reopened = AuditLog.for_file(path, KEY)
    assert reopened.verify().ok
    assert [entry.resource for entry in reopened.entries()] == ["before", "partial"]


def test_append_refuses_to_reanchor_modified_history_without_a_pending_transaction(
    tmp_path: Path,
) -> None:
    path = tmp_path / "audit.jsonl"
    log = AuditLog.for_file(path, KEY)
    log.append(_event("before"))
    path.with_suffix(".jsonl.anchor").unlink()
    with pytest.raises(AuditIntegrityError, match="ancla"):
        log.append(_event("must-not-heal"))
    assert len(path.read_text().splitlines()) == 1
    assert not log.verify().ok
