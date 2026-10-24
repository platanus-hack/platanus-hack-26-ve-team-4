import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from agent_zero.telemetry.audit_anchor import sign_anchor
from agent_zero.telemetry.audit_hashing import compute_hash
from agent_zero.telemetry.audit_log import AuditLog
from agent_zero.telemetry.audit_schemas import GENESIS_HASH, AuditDecision, AuditEntry, AuditEvent

KEY = b"clave-de-auditoria-de-prueba"


def _clock() -> datetime:
    return datetime(2026, 10, 24, 12, 0, tzinfo=UTC)


def _event(resource: str, decision: AuditDecision = AuditDecision.ALLOW) -> AuditEvent:
    return AuditEvent(actor="agent-1", action="tool.call", resource=resource, decision=decision)


def _fill(log: AuditLog, count: int = 3) -> None:
    for i in range(count):
        log.append(_event(f"res-{i}"))


def _rewrite_history(path: Path, key: bytes, mutate: Callable[[dict[str, Any]], None]) -> None:
    previous = GENESIS_HASH
    rewritten: list[str] = []
    for line in path.read_text().splitlines():
        record = json.loads(line)
        mutate(record)
        record["prev_hash"] = previous
        entry = AuditEntry.model_validate({**record, "hash": ""})
        record["hash"] = compute_hash(entry, key)
        previous = record["hash"]
        rewritten.append(json.dumps(record))
    path.write_text("\n".join(rewritten) + "\n")


@pytest.mark.requirement("OBS-02")
def test_history_rewritten_without_the_key_is_detected(tmp_path: Path) -> None:
    path = tmp_path / "a.jsonl"
    log = AuditLog.for_file(path, KEY, _clock)
    for i in range(3):
        log.append(_event(f"res-{i}", AuditDecision.DENY))
    _rewrite_history(path, b"clave-del-atacante", lambda record: record.update(decision="allow"))
    result = log.verify()
    assert not result.ok
    assert result.broken_at == 0


@pytest.mark.requirement("OBS-02")
def test_history_rewritten_with_valid_signatures_still_breaks_the_signed_anchor(
    tmp_path: Path,
) -> None:
    path = tmp_path / "a.jsonl"
    log = AuditLog.for_file(path, KEY, _clock)
    for i in range(3):
        log.append(_event(f"res-{i}", AuditDecision.DENY))
    anchor_path = path.with_suffix(".jsonl.anchor")
    stale = anchor_path.read_text()
    log.append(_event("res-3", AuditDecision.DENY))
    anchor_path.write_text(stale)
    result = log.verify()
    assert not result.ok
    assert "ancla" in result.detail


@pytest.mark.requirement("OBS-02")
def test_emptying_or_truncating_the_file_is_detected(tmp_path: Path) -> None:
    path = tmp_path / "a.jsonl"
    log = AuditLog.for_file(path, KEY, _clock)
    _fill(log, 4)
    lines = path.read_text().splitlines()
    path.write_text("\n".join(lines[:2]) + "\n")
    assert not log.verify().ok
    path.write_text("")
    emptied = log.verify()
    assert not emptied.ok
    assert emptied.entries == 0


@pytest.mark.requirement("OBS-02")
def test_missing_or_forged_anchor_is_detected(tmp_path: Path) -> None:
    path = tmp_path / "a.jsonl"
    log = AuditLog.for_file(path, KEY, _clock)
    _fill(log, 2)
    anchor_path = path.with_suffix(".jsonl.anchor")
    anchor_path.write_text("basura\n")
    assert not log.verify().ok
    forged = sign_anchor(b"clave-del-atacante", 2, log.entries()[-1].hash)
    anchor_path.write_text(forged)
    assert not log.verify().ok
    anchor_path.unlink()
    assert not log.verify().ok


@pytest.mark.requirement("OBS-02")
def test_a_log_reopened_with_the_same_key_keeps_verifying(tmp_path: Path) -> None:
    path = tmp_path / "a.jsonl"
    _fill(AuditLog.for_file(path, KEY, _clock), 2)
    reopened = AuditLog.for_file(path, KEY, _clock)
    reopened.append(_event("res-2"))
    assert reopened.verify().ok
    assert not AuditLog.for_file(path, b"otra-clave", _clock).verify().ok
