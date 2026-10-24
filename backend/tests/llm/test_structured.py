import pytest

from agent_zero.llm.errors import StructuredOutputError
from agent_zero.llm.instrumented_model import InstrumentedModel
from agent_zero.llm.ledger import MemoryCallLedger
from agent_zero.llm.playback_model import PlaybackModel
from agent_zero.llm.structured import structured_call
from tests.llm.streams import PROMPT, Verdict


async def test_valid_output_needs_no_repair() -> None:
    model = PlaybackModel([{"label": "ok"}])

    assert await structured_call(model, Verdict, PROMPT) == Verdict(label="ok")
    assert len(model.calls) == 1


async def test_invalid_output_is_repaired_with_the_validation_error() -> None:
    model = PlaybackModel([{"etiqueta": "mal"}, {"label": "ok"}])

    result = await structured_call(model, Verdict, PROMPT, repair_budget=1)

    assert result == Verdict(label="ok")
    repair_turn = model.calls[1]["messages"][-1]["content"][0]["text"]
    assert "Verdict" in repair_turn
    assert "label" in repair_turn


async def test_exhausted_budget_raises_with_the_attempt_count() -> None:
    model = PlaybackModel([{"etiqueta": "mal"}, {"etiqueta": "peor"}])

    with pytest.raises(StructuredOutputError) as failure:
        await structured_call(model, Verdict, PROMPT, repair_budget=1)

    assert failure.value.attempts == 2


async def test_every_attempt_reaches_the_ledger() -> None:
    ledger = MemoryCallLedger()
    model = InstrumentedModel(
        PlaybackModel([{"etiqueta": "mal"}, {"label": "ok"}]), "analyzer", ledger
    )

    await structured_call(model, Verdict, PROMPT)

    assert len(ledger.records()) == 2


async def test_negative_budget_is_rejected() -> None:
    with pytest.raises(ValueError, match="negativo"):
        await structured_call(PlaybackModel(), Verdict, PROMPT, repair_budget=-1)
