import pytest

from agent_zero.llm.playback_model import PlaybackModel
from agent_zero.llm.retrying_model import RetryingModel
from tests.llm.streams import PROMPT, Verdict, drain, output_of, text_of


async def no_sleep(_seconds: float) -> None:
    return None


def retrying(model: PlaybackModel, attempts: int = 3) -> RetryingModel:
    return RetryingModel(model, attempts=attempts, sleep=no_sleep, jitter=lambda: 0.0)


async def test_transient_errors_are_retried_with_exponential_backoff() -> None:
    model = retrying(PlaybackModel([TimeoutError(), ConnectionError(), "hola"]))

    events = await drain(model.stream(PROMPT))

    assert text_of(events) == "hola"
    assert model.waits == [0.5, 1.0]


async def test_structured_output_is_retried_too() -> None:
    model = retrying(PlaybackModel([TimeoutError(), {"label": "ok"}]))

    assert output_of(await drain(model.structured_output(Verdict, PROMPT))) == Verdict(label="ok")


async def test_permanent_errors_are_not_retried() -> None:
    inner = PlaybackModel([ValueError("schema"), "nunca"])

    with pytest.raises(ValueError, match="schema"):
        await drain(retrying(inner).stream(PROMPT))

    assert len(inner.calls) == 1


async def test_last_transient_error_surfaces_when_attempts_run_out() -> None:
    inner = PlaybackModel([TimeoutError("1"), TimeoutError("2")])

    with pytest.raises(TimeoutError, match="2"):
        await drain(retrying(inner, attempts=2).stream(PROMPT))


def test_attempts_must_be_positive() -> None:
    with pytest.raises(ValueError, match="al menos 1"):
        RetryingModel(PlaybackModel(), attempts=0)
