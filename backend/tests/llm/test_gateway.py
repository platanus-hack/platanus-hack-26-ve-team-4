from datetime import date

import pytest

from agent_zero.llm.gateway import LlmGateway
from agent_zero.llm.instrumented_model import InstrumentedModel
from agent_zero.llm.ledger import MemoryCallLedger
from agent_zero.llm.limits import LimitPolicy, ModelLimits
from agent_zero.llm.models import LlmMode, ModelRole
from agent_zero.llm.playback_model import PlaybackModel
from agent_zero.llm.quota import InMemoryCallQuota
from tests.llm.streams import PROMPT, Verdict


def model_limits() -> ModelLimits:
    policy = LimitPolicy(
        daily_calls=10,
        session_calls=10,
        campaign_calls=10,
        campaign_tokens=1_000,
        daily_usd=5.0,
        breaker_failures=3,
        breaker_recovery_seconds=30,
    )
    return ModelLimits(policy, InMemoryCallQuota(), lambda: 0.0, lambda: date(2026, 10, 24))


async def test_structured_calls_are_routed_by_role_and_summarized() -> None:
    ledger = MemoryCallLedger()
    models = {
        role: InstrumentedModel(PlaybackModel([{"label": role.value}]), role.value, ledger)
        for role in ModelRole
    }
    gateway = LlmGateway(LlmMode.OFFLINE, models, ledger, model_limits())

    result = await gateway.structured(ModelRole.ANALYZER, Verdict, PROMPT)

    assert result == Verdict(label="analyzer")
    assert [usage.role for usage in gateway.usage()] == ["analyzer"]


def test_every_role_needs_a_model() -> None:
    with pytest.raises(ValueError, match="victim"):
        LlmGateway(LlmMode.OFFLINE, {}, MemoryCallLedger(), model_limits())
