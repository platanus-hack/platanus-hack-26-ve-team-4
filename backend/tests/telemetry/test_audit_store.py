from pathlib import Path

from agent_zero.telemetry.audit_store import FileAuditStore, MemoryAuditStore


def test_memory_store_returns_copies() -> None:
    store = MemoryAuditStore()
    store.append_line("uno")
    store.read_lines().append("intruso")
    assert store.read_lines() == ["uno"]


def test_file_store_keeps_its_own_appends_without_rereading(tmp_path: Path) -> None:
    store = FileAuditStore(tmp_path / "a.jsonl")
    assert store.read_lines() == []
    store.append_line("uno")
    assert store.read_lines() == ["uno"]
    store.append_line("dos")
    assert store.read_lines() == ["uno", "dos"]
    assert (tmp_path / "a.jsonl").read_text() == "uno\ndos\n"


def test_file_store_rereads_after_an_outside_write(tmp_path: Path) -> None:
    path = tmp_path / "a.jsonl"
    store = FileAuditStore(path)
    store.append_line("uno")
    store.read_lines()
    path.write_text("otro\n")
    assert store.read_lines() == ["otro"]
    with path.open("a") as handle:
        handle.write("ajeno\n")
    store.append_line("tres")
    assert store.read_lines() == ["otro", "ajeno", "tres"]


def test_two_stores_on_one_file_see_each_other(tmp_path: Path) -> None:
    path = tmp_path / "a.jsonl"
    first, second = FileAuditStore(path), FileAuditStore(path)
    first.append_line("uno")
    assert second.read_lines() == ["uno"]
    second.append_line("dos")
    assert first.read_lines() == ["uno", "dos"]
