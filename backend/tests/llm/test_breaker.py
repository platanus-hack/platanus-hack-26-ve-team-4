from agent_zero.llm.breaker import BreakerState, CircuitBreaker


def test_opens_after_consecutive_failures_and_recovers_half_open() -> None:
    breaker = CircuitBreaker(failure_threshold=2, recovery_seconds=10)

    breaker.record_failure(now=0)
    assert breaker.allow(now=1)
    breaker.record_failure(now=1)

    assert not breaker.allow(now=5)
    assert breaker.allow(now=11)
    assert breaker.state is BreakerState.HALF_OPEN


def test_failure_while_half_open_reopens_immediately() -> None:
    breaker = CircuitBreaker(failure_threshold=1, recovery_seconds=10)
    breaker.record_failure(now=0)
    breaker.allow(now=10)

    breaker.record_failure(now=10)

    assert breaker.state is BreakerState.OPEN
    assert not breaker.allow(now=15)


def test_success_closes_and_resets_the_count() -> None:
    breaker = CircuitBreaker(failure_threshold=2, recovery_seconds=10)
    breaker.record_failure(now=0)

    breaker.record_success()
    breaker.record_failure(now=1)

    assert breaker.state is BreakerState.CLOSED
