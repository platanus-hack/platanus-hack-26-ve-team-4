from agent_zero.llm.schemas import CallCost, CallUsage, ModelPrice, TokenPrice

TOKENS_PER_MTOK = 1_000_000

PRICES: dict[str, ModelPrice] = {
    "claude-haiku-5-5": ModelPrice(
        standard=TokenPrice(
            input_usd_per_mtok=0.10,
            output_usd_per_mtok=0.50,
            cache_read_usd_per_mtok=0.01,
            cache_write_usd_per_mtok=0.125,
        ),
        long_context=TokenPrice(
            input_usd_per_mtok=0.50,
            output_usd_per_mtok=2.50,
            cache_read_usd_per_mtok=0.05,
            cache_write_usd_per_mtok=0.625,
        ),
        long_context_threshold=100_000,
    ),
}


class UnpricedModelError(LookupError):
    pass


def price_for(model_id: str) -> ModelPrice:
    price = PRICES.get(model_id)
    if price is None:
        raise UnpricedModelError(f"no hay precio registrado para {model_id}")
    return price


def _charged(tokens: int, usd_per_mtok: float) -> float:
    return tokens * usd_per_mtok / TOKENS_PER_MTOK


def cost_for(model_id: str, usage: CallUsage) -> CallCost:
    rate = price_for(model_id).for_prompt(usage.prompt_tokens)
    return CallCost(
        input_usd=_charged(usage.input_tokens, rate.input_usd_per_mtok),
        output_usd=_charged(usage.output_tokens, rate.output_usd_per_mtok),
        cache_read_usd=_charged(usage.cache_read_tokens, rate.cache_read_usd_per_mtok),
        cache_write_usd=_charged(usage.cache_write_tokens, rate.cache_write_usd_per_mtok),
    )


def cost_or_none(model_id: str, usage: CallUsage) -> CallCost | None:
    try:
        return cost_for(model_id, usage)
    except UnpricedModelError:
        return None
