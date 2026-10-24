from pathlib import Path

import pytest

from agent_zero.telemetry.audit_anchor import FileAnchor, MemoryAnchor, anchor_matches, sign_anchor

KEY = b"clave"


@pytest.mark.requirement("OBS-02")
def test_signed_anchor_matches_only_its_own_state() -> None:
    raw = sign_anchor(KEY, 3, "abc")
    assert anchor_matches(KEY, raw, 3, "abc")
    assert not anchor_matches(KEY, raw, 2, "abc")
    assert not anchor_matches(KEY, raw, 3, "xyz")
    assert not anchor_matches(b"otra", raw, 3, "abc")
    assert not anchor_matches(KEY, None, 3, "abc")
    assert not anchor_matches(KEY, "no es json", 3, "abc")


def test_stores_round_trip(tmp_path: Path) -> None:
    memory = MemoryAnchor()
    assert memory.read() is None
    memory.write("x")
    assert memory.read() == "x"
    file = FileAnchor(tmp_path / "sub" / "a.anchor")
    assert file.read() is None
    file.write("y")
    file.write("z")
    assert file.read() == "z"
