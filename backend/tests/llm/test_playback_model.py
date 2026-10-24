import pytest

from agent_zero.llm.playback_model import PlaybackExhaustedError, PlaybackModel, Refusal
from agent_zero.llm.usage import stop_reason_from_event
from tests.llm.streams import PROMPT, Verdict, drain, output_of, text_of


async def test_scripted_text_and_structured_output_play_in_order() -> None:
    model = PlaybackModel(["respuesta", {"label": "ok"}, Verdict(label="directo")])

    assert text_of(await drain(model.stream(PROMPT))) == "respuesta"
    assert output_of(await drain(model.structured_output(Verdict, PROMPT))) == Verdict(label="ok")
    assert output_of(await drain(model.structured_output(Verdict, PROMPT))).label == "directo"
    assert [call["kind"] for call in model.calls] == [
        "stream",
        "structured_output",
        "structured_output",
    ]


async def test_empty_script_fails_loudly() -> None:
    with pytest.raises(PlaybackExhaustedError, match="número 1"):
        await drain(PlaybackModel().stream(PROMPT))


async def test_scripted_exception_is_raised() -> None:
    model = PlaybackModel([TimeoutError("lento")])

    with pytest.raises(TimeoutError):
        await drain(model.stream(PROMPT))


async def test_refusal_ends_stream_with_refusal_stop_reason() -> None:
    events = await drain(PlaybackModel([Refusal()]).stream(PROMPT))

    assert stop_reason_from_event(events[-1]) == "refusal"


async def test_structured_refusal_reports_stop_reason_then_raises() -> None:
    seen: list[object] = []

    async def consume() -> None:
        async for event in PlaybackModel([Refusal()]).structured_output(Verdict, PROMPT):
            seen.append(event)

    with pytest.raises(ValueError, match="refusal"):
        await consume()
    assert stop_reason_from_event(seen[0]) == "refusal"
