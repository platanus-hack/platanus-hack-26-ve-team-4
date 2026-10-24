from strands.models.anthropic import AnthropicModel

from agent_zero.llm.call_watch import UNKNOWN_MODEL, CallWatch, call_origin, model_id_of
from agent_zero.llm.context import declaring_prompt_version
from agent_zero.llm.models import CallKind, CallOrigin, CallOutcome
from agent_zero.llm.playback_model import PlaybackModel
from agent_zero.llm.retrying_model import RetryingModel
from agent_zero.llm.schemas import CallScope, CallUsage
from agent_zero.llm.usage import usage_metadata
from agent_zero.shared.clock import utc_now


def anthropic_model() -> AnthropicModel:
    return AnthropicModel(
        client_args={"api_key": "sk-prueba"}, model_id="claude-haiku-5-5", max_tokens=256
    )


def test_origin_follows_the_wrapped_chain() -> None:
    assert call_origin(RetryingModel(anthropic_model())) is CallOrigin.LIVE
    assert call_origin(RetryingModel(PlaybackModel())) is CallOrigin.SIMULATED


def test_model_id_falls_back_when_config_has_none() -> None:
    model = PlaybackModel(model_id="")

    assert model_id_of(model) == UNKNOWN_MODEL
    assert model_id_of(anthropic_model()) == "claude-haiku-5-5"


def test_record_prices_observed_usage_and_keeps_scope() -> None:
    model = PlaybackModel(model_id="claude-haiku-5-5")
    watch = CallWatch(model, "victim", CallKind.STREAM, CallScope(session_id="sess-1"))
    watch.observe(usage_metadata(CallUsage(input_tokens=1_000, output_tokens=100)))
    watch.observe({"messageStop": {"stopReason": "refusal"}})

    with declaring_prompt_version("victim-v1"):
        record = watch.record(CallOutcome.REFUSED, utc_now())

    assert watch.refused
    assert record.cost is not None
    assert record.cost.total_usd > 0
    assert record.prompt_version == "victim-v1"
    assert record.scope.session_id == "sess-1"
    assert record.origin is CallOrigin.SIMULATED
