import pytest

from agent_zero.agent_gateway.rate_limiter import RateLimiter
from tests.identity.conftest import FakeClock


@pytest.mark.requirement("GW-02")
def test_limit_is_per_key_and_window_slides() -> None:
    clock = FakeClock()
    limiter = RateLimiter(2, clock)
    assert limiter.allow("a")
    assert limiter.allow("a")
    assert not limiter.allow("a")
    assert limiter.allow("b")
    clock.advance(seconds=59)
    assert not limiter.allow("a")
    clock.advance(seconds=1)
    assert limiter.allow("a")


def test_denied_calls_do_not_extend_the_window() -> None:
    clock = FakeClock()
    limiter = RateLimiter(1, clock)
    assert limiter.allow("a")
    for _ in range(5):
        clock.advance(seconds=10)
        assert not limiter.allow("a")
    clock.advance(seconds=10)
    assert limiter.allow("a")
