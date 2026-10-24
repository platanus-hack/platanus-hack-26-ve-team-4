import pytest

from agent_zero.evals.wilson_interval import wilson_interval


def test_empty_sample_has_no_interval() -> None:
    assert wilson_interval(0, 0) is None


def test_interval_for_known_values() -> None:
    low, high = wilson_interval(8, 10) or (0.0, 0.0)

    assert low == pytest.approx(0.4902, abs=1e-3)
    assert high == pytest.approx(0.9433, abs=1e-3)


def test_zero_successes_keeps_an_honest_upper_bound() -> None:
    low, high = wilson_interval(0, 8) or (1.0, 0.0)

    assert low == 0.0
    assert high == pytest.approx(0.3244, abs=1e-3)


def test_interval_narrows_with_more_data() -> None:
    small = wilson_interval(0, 8) or (0.0, 1.0)
    large = wilson_interval(0, 80) or (0.0, 1.0)

    assert large[1] < small[1]
