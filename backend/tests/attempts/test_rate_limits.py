from datetime import UTC, datetime, timedelta

import pytest

from agent_zero.attempts.errors import QueueFullError, TooFrequentError
from agent_zero.attempts.rate_limits import check_queue_capacity, check_session_interval

NOW = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)


def test_first_attempt_of_a_session_is_allowed() -> None:
    check_session_interval(None, NOW, 3)


def test_attempt_after_the_interval_is_allowed() -> None:
    check_session_interval(NOW - timedelta(seconds=3), NOW, 3)


def test_attempt_within_the_interval_says_how_long_to_wait() -> None:
    with pytest.raises(TooFrequentError) as caught:
        check_session_interval(NOW - timedelta(seconds=0.5), NOW, 3)

    assert caught.value.retry_after == 3


def test_queue_rejects_at_its_limit() -> None:
    check_queue_capacity(19, 20)
    with pytest.raises(QueueFullError):
        check_queue_capacity(20, 20)
