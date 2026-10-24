import os
from collections.abc import Mapping

from strands.models.anthropic import AnthropicModel
from strands.models.model import CacheConfig, Model

from agent_zero.config import Settings
from agent_zero.llm.cassette import CassetteWriter, load_cassette
from agent_zero.llm.cassette_model import CassetteModel
from agent_zero.llm.catalog import model_for, profile_for
from agent_zero.llm.gateway import LlmGateway
from agent_zero.llm.instrumented_model import InstrumentedModel
from agent_zero.llm.ledger import JsonlCallLedger
from agent_zero.llm.limits import LimitPolicy, ModelLimits
from agent_zero.llm.models import LlmMode, ModelRole
from agent_zero.llm.playback_model import PlaybackModel
from agent_zero.llm.quota import InMemoryCallQuota
from agent_zero.llm.recording_model import RecordingModel
from agent_zero.llm.retrying_model import RetryingModel

SDK_KEY_VARIABLE = "ANTHROPIC_API_KEY"


class LlmConfigurationError(RuntimeError):
    pass


def _api_key(settings: Settings) -> str | None:
    key = settings.llm_api_key.get_secret_value() or os.environ.get(SDK_KEY_VARIABLE, "")
    if not key:
        mode = settings.llm_mode.value
        raise LlmConfigurationError(
            f"el modo {mode} necesita AGENT_ZERO_LLM_API_KEY o {SDK_KEY_VARIABLE}"
        )
    return key


def build_provider(role: ModelRole, settings: Settings) -> AnthropicModel:
    profile = profile_for(role)
    return AnthropicModel(
        client_args={
            "api_key": _api_key(settings),
            "max_retries": 0,
            "timeout": settings.llm_timeout_seconds,
        },
        model_id=model_for(role, settings),
        max_tokens=profile.max_tokens,
        params={
            "output_config": {"effort": profile.effort},
            "thinking": {"type": profile.thinking},
        },
        cache_config=CacheConfig(strategy="anthropic", system_prompt_ttl=True, tools_ttl=True),
    )


def _base_model(
    role: ModelRole, settings: Settings, playback: Mapping[ModelRole, PlaybackModel]
) -> Model:
    mode = settings.llm_mode
    if mode is LlmMode.OFFLINE:
        return playback.get(role) or PlaybackModel(model_id=model_for(role, settings))
    if mode is LlmMode.REPLAY:
        return CassetteModel(load_cassette(settings.llm_default_cassette_path), role.value)
    provider: Model = build_provider(role, settings)
    if mode is LlmMode.RECORD:
        provider = RecordingModel(
            provider, CassetteWriter(settings.llm_default_cassette_path), role.value
        )
    return RetryingModel(provider, attempts=settings.llm_retry_attempts)


def build_gateway(
    settings: Settings, playback: Mapping[ModelRole, PlaybackModel] | None = None
) -> LlmGateway:
    ledger = JsonlCallLedger(settings.llm_ledger_path)
    limits = ModelLimits(LimitPolicy.from_settings(settings), InMemoryCallQuota())
    limits.charge_history(ledger.records())
    models: dict[ModelRole, Model] = {
        role: InstrumentedModel(
            _base_model(role, settings, playback or {}), role.value, ledger, limits
        )
        for role in ModelRole
    }
    return LlmGateway(settings.llm_mode, models, ledger, limits)
