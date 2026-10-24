from datetime import UTC, datetime
from pathlib import Path

import pytest

from agent_zero.config import Settings
from agent_zero.telemetry.audit_hashing import compute_hash, derive_audit_key
from agent_zero.telemetry.audit_schemas import GENESIS_HASH, AuditDecision, AuditEntry


def _entry() -> AuditEntry:
    return AuditEntry(
        sequence=0,
        at=datetime(2026, 10, 24, tzinfo=UTC),
        actor="a",
        action="x",
        resource="r",
        decision=AuditDecision.ALLOW,
        prev_hash=GENESIS_HASH,
        hash="",
    )


@pytest.mark.requirement("OBS-02")
def test_hash_depends_on_the_key() -> None:
    entry = _entry()
    assert compute_hash(entry, b"uno") == compute_hash(entry, b"uno")
    assert compute_hash(entry, b"uno") != compute_hash(entry, b"dos")


@pytest.mark.requirement("OBS-02")
def test_audit_key_is_derived_from_the_signing_key_not_equal_to_it(tmp_path: Path) -> None:
    first = Settings(data_dir=tmp_path, identity_signing_key="a" * 40)
    second = Settings(data_dir=tmp_path, identity_signing_key="b" * 40)
    assert derive_audit_key(first) != derive_audit_key(second)
    assert derive_audit_key(first) != b"a" * 40
