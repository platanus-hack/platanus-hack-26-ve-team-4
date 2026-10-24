from pathlib import Path

import pytest
from pydantic import SecretStr

from agent_zero.config import Settings
from agent_zero.llm.call_watch import call_origin
from agent_zero.llm.cassette import CassetteEntry, CassetteWriter
from agent_zero.llm.events import text_events
from agent_zero.llm.factory import (
    SDK_KEY_VARIABLE,
    LlmConfigurationError,
    build_gateway,
    build_provider,
)
from agent_zero.llm.models import CallKind, CallOrigin, LlmMode, ModelRole
from agent_zero.llm.playback_model import PlaybackModel
from tests.llm.streams import PROMPT, drain, text_of


def settings(tmp_path: Path, mode: LlmMode, key: str = "") -> Settings:
    return Settings(data_dir=tmp_path, llm_mode=mode, llm_api_key=SecretStr(key))


def test_provider_carries_role_profile_and_never_sampling_params(tmp_path: Path) -> None:
    provider = build_provider(ModelRole.ANALYZER, settings(tmp_path, LlmMode.LIVE, "sk-prueba"))

    config = provider.get_config()
    assert config["model_id"] == "claude-haiku-5-5"
    assert config["max_tokens"] == 8192
    assert config["params"] == {
        "output_config": {"effort": "medium"},
        "thinking": {"type": "adaptive"},
    }
    assert provider.client.max_retries == 0


def test_live_mode_without_key_fails_at_startup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(SDK_KEY_VARIABLE, raising=False)

    with pytest.raises(LlmConfigurationError, match="API_KEY"):
        build_gateway(settings(tmp_path, LlmMode.LIVE))


def test_live_gateway_wraps_the_anthropic_provider(tmp_path: Path) -> None:
    gateway = build_gateway(settings(tmp_path, LlmMode.RECORD, "sk-prueba"))

    chain = []
    current: object = gateway.model(ModelRole.VICTIM)
    while current is not None:
        chain.append(type(current).__name__)
        current = vars(current).get("inner")
    assert call_origin(gateway.model(ModelRole.VICTIM)) is CallOrigin.LIVE
    assert chain == ["InstrumentedModel", "RetryingModel", "RecordingModel", "AnthropicModel"]


async def test_offline_gateway_uses_the_given_scripts(tmp_path: Path) -> None:
    gateway = build_gateway(
        settings(tmp_path, LlmMode.OFFLINE), {ModelRole.VICTIM: PlaybackModel(["hola"])}
    )

    events = await drain(gateway.model(ModelRole.VICTIM).stream(PROMPT))

    assert text_of(events) == "hola"
    assert gateway.ledger.records()[0].origin is CallOrigin.SIMULATED


async def test_replay_gateway_reads_the_cassette(tmp_path: Path) -> None:
    current = settings(tmp_path, LlmMode.REPLAY)
    CassetteWriter(current.llm_default_cassette_path).append(
        CassetteEntry(
            role="prober",
            kind=CallKind.STREAM,
            events=[dict(event) for event in text_events("grabado")],
        )
    )

    gateway = build_gateway(current)

    assert text_of(await drain(gateway.model(ModelRole.PROBER).stream(PROMPT))) == "grabado"
    assert gateway.ledger.records()[0].origin is CallOrigin.REPLAYED
