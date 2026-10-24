import fcntl
import os
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path
from typing import Protocol


class AuditStore(Protocol):
    def locked(self) -> AbstractContextManager[None]: ...

    def read_lines(self) -> list[str]: ...

    def append_line(self, line: str) -> None: ...


class MemoryAuditStore:
    def __init__(self) -> None:
        self.lines: list[str] = []

    @contextmanager
    def locked(self) -> Iterator[None]:
        yield

    def read_lines(self) -> list[str]:
        return list(self.lines)

    def append_line(self, line: str) -> None:
        self.lines.append(line)


class FileAuditStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    @contextmanager
    def locked(self) -> Iterator[None]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        with lock_path.open("a", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def read_lines(self) -> list[str]:
        if not self.path.exists():
            return []
        return [line for line in self.path.read_text(encoding="utf-8").splitlines() if line]

    def append_line(self, line: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
            handle.flush()
            os.fsync(handle.fileno())
