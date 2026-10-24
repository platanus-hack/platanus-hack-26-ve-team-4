import pytest

from agent_zero.llm.pricing import UnpricedModelError, cost_for, cost_or_none
from agent_zero.llm.schemas import CallUsage


def test_haiku_standard_rate_applies_up_to_100k_prompt_tokens() -> None:
    usage = CallUsage(input_tokens=100_000, output_tokens=1_000_000)

    cost = cost_for("claude-haiku-5-5", usage)

    assert cost.input_usd == pytest.approx(0.01)
    assert cost.output_usd == pytest.approx(0.50)


def test_cache_tokens_count_towards_the_long_context_threshold() -> None:
    usage = CallUsage(input_tokens=1_000, cache_read_tokens=100_000, output_tokens=1_000)

    cost = cost_for("claude-haiku-5-5", usage)

    assert cost.input_usd == pytest.approx(1_000 * 0.50 / 1_000_000)
    assert cost.cache_read_usd == pytest.approx(100_000 * 0.05 / 1_000_000)
    assert cost.output_usd == pytest.approx(1_000 * 2.50 / 1_000_000)


def test_unknown_model_is_reported_as_unpriced() -> None:
    usage = CallUsage(input_tokens=10)

    with pytest.raises(UnpricedModelError):
        cost_for("claude-desconocido", usage)
    assert cost_or_none("claude-desconocido", usage) is None
