from pathlib import Path
from typing import Protocol


class AuditStore(Protocol):
    def read_lines(self) -> list[str]: ...

    def append_line(self, line: str) -> None: ...


class MemoryAuditStore:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def read_lines(self) -> list[str]:
        return list(self.lines)

    def append_line(self, line: str) -> None:
        self.lines.append(line)


class FileAuditStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def read_lines(self) -> list[str]:
        if not self.path.exists():
            return []
        return [line for line in self.path.read_text(encoding="utf-8").splitlines() if line]

    def append_line(self, line: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
            handle.flush()
