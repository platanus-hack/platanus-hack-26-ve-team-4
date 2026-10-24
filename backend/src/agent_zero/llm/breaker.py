from enum import StrEnum


class BreakerState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_seconds: float = 30.0) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold debe ser positivo")
        if recovery_seconds <= 0:
            raise ValueError("recovery_seconds debe ser positivo")
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self.consecutive_failures = 0
        self.opened_at: float | None = None
        self.state = BreakerState.CLOSED

    def allow(self, now: float) -> bool:
        if self.state is BreakerState.OPEN and self._recovered(now):
            self.state = BreakerState.HALF_OPEN
        return self.state is not BreakerState.OPEN

    def record_success(self) -> None:
        self.consecutive_failures = 0
        self.opened_at = None
        self.state = BreakerState.CLOSED

    def record_failure(self, now: float) -> None:
        self.consecutive_failures += 1
        if (
            self.state is BreakerState.HALF_OPEN
            or self.consecutive_failures >= self.failure_threshold
        ):
            self.opened_at = now
            self.state = BreakerState.OPEN

    def _recovered(self, now: float) -> bool:
        return self.opened_at is not None and now >= self.opened_at + self.recovery_seconds
