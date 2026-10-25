import json
import threading
from datetime import UTC, datetime
from pathlib import Path

import pytest

from agent_zero.config import Settings
from agent_zero.telemetry import audit_verifier
from agent_zero.telemetry.audit_anchor import MemoryAnchor
from agent_zero.telemetry.audit_log import AuditLog
from agent_zero.telemetry.audit_schemas import GENESIS_HASH, AuditDecision, AuditEvent
from agent_zero.telemetry.audit_store import MemoryAuditStore
from agent_zero.telemetry.errors import AuditIntegrityError
from agent_zero.telemetry.otel_setup import build_telemetry
from agent_zero.telemetry.spans import traced_span

KEY = b"clave-de-auditoria-de-prueba"


def _clock() -> datetime:
    return datetime(2026, 10, 24, 12, 0, tzinfo=UTC)


def _event(
    resource: str,
    decision: AuditDecision = AuditDecision.ALLOW,
    reason: str = "",
    attributes: dict[str, int] | None = None,
) -> AuditEvent:
    return AuditEvent(
        actor="agent-1",
        action="tool.call",
        resource=resource,
        decision=decision,
        reason=reason,
        attributes=dict(attributes or {}),
    )


def _fill(log: AuditLog, count: int = 3) -> None:
    for i in range(count):
        log.append(_event(f"res-{i}", attributes={"n": i}))


@pytest.mark.requirement("OBS-02")
def test_valid_chain_verifies(tmp_path: Path) -> None:
    log = AuditLog.for_file(tmp_path / "a.jsonl", KEY, _clock)
    _fill(log)
    result = log.verify()
    assert result.ok
    assert result.entries == 3
    assert result.broken_at is None
    entries = log.entries()
    assert entries[0].prev_hash == GENESIS_HASH
    assert entries[1].prev_hash == entries[0].hash


@pytest.mark.requirement("OBS-02")
def test_editing_a_line_breaks_at_that_line(tmp_path: Path) -> None:
    path = tmp_path / "a.jsonl"
    log = AuditLog.for_file(path, KEY, _clock)
    _fill(log, 4)
    lines = path.read_text().splitlines()
    record = json.loads(lines[2])
    record["decision"] = "deny"
    lines[2] = json.dumps(record)
    path.write_text("\n".join(lines) + "\n")
    result = log.verify()
    assert not result.ok
    assert result.broken_at == 2


@pytest.mark.requirement("OBS-02")
def test_rehashed_edit_breaks_next_link(tmp_path: Path) -> None:
    store = MemoryAuditStore()
    log = AuditLog(store, KEY, MemoryAnchor(), _clock)
    _fill(log, 3)
    record = json.loads(store.lines[0])
    record["reason"] = "cambiado"
    store.lines[0] = json.dumps(record)
    assert log.verify().broken_at == 0


@pytest.mark.requirement("OBS-02")
def test_garbage_line_is_reported(tmp_path: Path) -> None:
    path = tmp_path / "a.jsonl"
    log = AuditLog.for_file(path, KEY, _clock)
    _fill(log, 2)
    with path.open("a") as handle:
        handle.write("no es json\n")
    assert log.verify().broken_at == 2


@pytest.mark.requirement("OBS-02")
def test_empty_log_is_valid(tmp_path: Path) -> None:
    assert AuditLog.for_file(tmp_path / "x.jsonl", KEY).verify().ok


@pytest.mark.requirement("OBS-02")
def test_in_memory_variant_and_settings_path(tmp_path: Path) -> None:
    memory = AuditLog.in_memory(_clock)
    _fill(memory)
    assert memory.verify().ok
    settings = Settings(data_dir=tmp_path)
    log = AuditLog.from_settings(settings, _clock)
    _fill(log, 1)
    assert settings.audit_log_path.exists()


@pytest.mark.requirement("OBS-02")
def test_trace_and_span_ids_come_from_active_span(tmp_path: Path) -> None:
    telemetry = build_telemetry(Settings(data_dir=tmp_path, otel_exporter="memory"))
    log = AuditLog.in_memory(_clock)
    with traced_span(telemetry.tracer, "run") as span:
        entry = log.append(_event("r", AuditDecision.DENY, "bloqueado"))
        context = span.raw.get_span_context()
    outside = log.append(_event("r", AuditDecision.INFO))
    assert entry.trace_id == format(context.trace_id, "032x")
    assert entry.span_id == format(context.span_id, "016x")
    assert outside.trace_id is None
    assert outside.span_id is None
    telemetry.shutdown()


@pytest.mark.requirement("OBS-02")
def test_concurrent_writes_keep_chain_valid(tmp_path: Path) -> None:
    log = AuditLog.for_file(tmp_path / "a.jsonl", KEY, _clock)
    threads = [threading.Thread(target=_fill, args=(log, 10)) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    result = log.verify()
    assert result.ok
    assert result.entries == 60


@pytest.mark.requirement("OBS-02")
def test_append_refuses_history_edited_after_it_was_verified(tmp_path: Path) -> None:
    path = tmp_path / "a.jsonl"
    log = AuditLog.for_file(path, KEY, _clock)
    _fill(log, 4)
    lines = path.read_text().splitlines()
    record = json.loads(lines[1])
    record["decision"] = "deny"
    lines[1] = json.dumps(record)
    path.write_text("\n".join(lines) + "\n")
    with pytest.raises(AuditIntegrityError):
        log.append(_event("must-not-extend"))
    assert len(path.read_text().splitlines()) == 4


def test_append_checks_only_lines_it_has_not_verified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    log = AuditLog.for_file(tmp_path / "a.jsonl", KEY, _clock)
    _fill(log, 5)
    checked: list[int] = []
    original = audit_verifier._line_problem

    def counting(line: str, index: int, expected_prev: str, key: bytes) -> str | None:
        checked.append(index)
        return original(line, index, expected_prev, key)

    monkeypatch.setattr(audit_verifier, "_line_problem", counting)
    log.append(_event("next"))
    assert checked == []
    assert log.verify().ok
    assert checked == list(range(6))


def test_entries_reparse_when_history_changes_underneath(tmp_path: Path) -> None:
    path = tmp_path / "a.jsonl"
    log = AuditLog.for_file(path, KEY, _clock)
    _fill(log, 3)
    assert [entry.resource for entry in log.entries()] == ["res-0", "res-1", "res-2"]
    log.append(_event("res-3"))
    assert [entry.resource for entry in log.entries()][-1] == "res-3"
    lines = path.read_text().splitlines()
    record = json.loads(lines[0])
    record["resource"] = "editado"
    lines[0] = json.dumps(record)
    path.write_text("\n".join(lines) + "\n")
    assert log.entries()[0].resource == "editado"
