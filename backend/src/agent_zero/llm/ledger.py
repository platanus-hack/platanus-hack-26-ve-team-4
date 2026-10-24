import threading
from pathlib import Path
from typing import Protocol, runtime_checkable

from agent_zero.llm.schemas import CallRecord


class LedgerFormatError(ValueError):
    pass


@runtime_checkable
class CallLedger(Protocol):
    def append(self, record: CallRecord) -> None: ...

    def records(self) -> list[CallRecord]: ...


class JsonlCallLedger:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: CallRecord) -> None:
        line = record.model_dump_json()
        with self._lock, self.path.open("a", encoding="utf-8") as handle:
            handle.write(f"{line}\n")

    def records(self) -> list[CallRecord]:
        return load_ledger(self.path) if self.path.exists() else []


class MemoryCallLedger:
    def __init__(self) -> None:
        self._records: list[CallRecord] = []

    def append(self, record: CallRecord) -> None:
        self._records.append(record)

    def records(self) -> list[CallRecord]:
        return list(self._records)


def load_ledger(path: Path) -> list[CallRecord]:
    records: list[CallRecord] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(CallRecord.model_validate_json(line))
        except ValueError as error:
            raise LedgerFormatError(f"{path}:{number}: {error}") from error
    return records
