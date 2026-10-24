import os
from pathlib import Path

import pytest

from agent_zero.config import Settings
from agent_zero.llm.factory import build_gateway
from agent_zero.llm.models import CallOrigin, CallOutcome, LlmMode, ModelRole
from tests.llm.streams import Verdict

LIVE_FLAG = "AGENT_ZERO_LLM_LIVE_SMOKE"

pytestmark = pytest.mark.skipif(
    os.environ.get(LIVE_FLAG) != "1",
    reason=f"llama a la API real y cuesta dinero: exportar {LIVE_FLAG}=1",
)


async def test_one_live_structured_call_is_priced_and_recorded(tmp_path: Path) -> None:
    gateway = build_gateway(Settings(data_dir=tmp_path, llm_mode=LlmMode.LIVE))

    verdict = await gateway.structured(
        ModelRole.ANALYZER,
        Verdict,
        [{"role": "user", "content": [{"text": "Clasifica 'hola' con label='saludo'."}]}],
    )

    [record] = gateway.ledger.records()
    assert verdict.label
    assert record.origin is CallOrigin.LIVE
    assert record.outcome is CallOutcome.OK
    assert record.cost is not None


async def test_one_live_victim_stream_runs_without_thinking(tmp_path: Path) -> None:
    gateway = build_gateway(Settings(data_dir=tmp_path, llm_mode=LlmMode.LIVE))
    model = gateway.model(ModelRole.VICTIM)

    events = [
        event
        async for event in model.stream(
            [{"role": "user", "content": [{"text": "Responde solo: ok"}]}],
            system_prompt="Eres un agente de soporte breve.",
        )
    ]

    [record] = gateway.ledger.records()
    assert events
    assert record.outcome is CallOutcome.OK
    assert record.usage is not None
    assert record.usage.output_tokens < 50
