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


Stamp = tuple[int, int, int]


class FileAuditStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._cache: tuple[Stamp, list[str]] | None = None

    def _stamp(self) -> Stamp:
        info = self.path.stat()
        return info.st_ino, info.st_size, info.st_mtime_ns

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
            self._cache = None
            return []
        stamp = self._stamp()
        if self._cache is not None and self._cache[0] == stamp:
            return list(self._cache[1])
        text = self.path.read_text(encoding="utf-8")
        lines = [line for line in text.splitlines() if line]
        self._cache = (stamp, lines)
        return list(lines)

    def append_line(self, line: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        current = self._cache
        if current is not None and (not self.path.exists() or current[0] != self._stamp()):
            current = None
        self._cache = None
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        if current is not None:
            self._cache = (self._stamp(), [*current[1], line])
