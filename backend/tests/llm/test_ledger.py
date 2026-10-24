from pathlib import Path

import pytest

from agent_zero.llm.ledger import JsonlCallLedger, LedgerFormatError, MemoryCallLedger, load_ledger
from tests.llm.records import call_record


def test_jsonl_ledger_persists_records_in_order(tmp_path: Path) -> None:
    ledger = JsonlCallLedger(tmp_path / "llm" / "calls.jsonl")
    first, second = call_record("prober"), call_record("victim")

    ledger.append(first)
    ledger.append(second)

    assert JsonlCallLedger(ledger.path).records() == [first, second]


def test_missing_ledger_file_has_no_records(tmp_path: Path) -> None:
    assert JsonlCallLedger(tmp_path / "calls.jsonl").records() == []


def test_corrupt_line_reports_its_location(tmp_path: Path) -> None:
    path = tmp_path / "calls.jsonl"
    path.write_text("{no es json}\n", encoding="utf-8")

    with pytest.raises(LedgerFormatError, match=r"calls.jsonl:1"):
        load_ledger(path)


def test_memory_ledger_returns_a_copy() -> None:
    ledger = MemoryCallLedger()
    ledger.append(call_record())

    ledger.records().clear()

    assert len(ledger.records()) == 1
