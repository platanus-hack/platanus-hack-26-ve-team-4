import threading
from collections import defaultdict
from collections.abc import Sequence
from typing import Protocol, runtime_checkable

Reservation = tuple[str, int]


@runtime_checkable
class CallQuota(Protocol):
    def reserve(self, reservations: Sequence[Reservation]) -> str | None: ...

    def add_tokens(self, key: str, tokens: int) -> None: ...

    def calls(self, key: str) -> int: ...

    def tokens(self, key: str) -> int: ...


class InMemoryCallQuota:
    def __init__(self) -> None:
        self._calls: defaultdict[str, int] = defaultdict(int)
        self._tokens: defaultdict[str, int] = defaultdict(int)
        self._lock = threading.Lock()

    def reserve(self, reservations: Sequence[Reservation]) -> str | None:
        with self._lock:
            for key, limit in reservations:
                if self._calls[key] >= limit:
                    return key
            for key, _ in reservations:
                self._calls[key] += 1
            return None

    def add_tokens(self, key: str, tokens: int) -> None:
        if tokens < 0:
            raise ValueError("tokens no puede ser negativo")
        with self._lock:
            self._tokens[key] += tokens

    def calls(self, key: str) -> int:
        return self._calls[key]

    def tokens(self, key: str) -> int:
        return self._tokens[key]
