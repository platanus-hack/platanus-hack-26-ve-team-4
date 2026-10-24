from collections import deque
from collections.abc import Callable
from datetime import datetime, timedelta

from agent_zero.shared.clock import utc_now

WINDOW = timedelta(minutes=1)


class RateLimiter:
    def __init__(self, limit_per_minute: int, clock: Callable[[], datetime] = utc_now) -> None:
        self._limit = limit_per_minute
        self._clock = clock
        self._calls: dict[str, deque[datetime]] = {}

    def allow(self, key: str) -> bool:
        now = self._clock()
        calls = self._calls.setdefault(key, deque())
        while calls and now - calls[0] >= WINDOW:
            calls.popleft()
        if len(calls) >= self._limit:
            return False
        calls.append(now)
        return True
