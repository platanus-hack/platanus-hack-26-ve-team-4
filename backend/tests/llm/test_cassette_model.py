import pytest

from agent_zero.llm.cassette import CassetteEntry
from agent_zero.llm.cassette_model import CassetteExhaustedError, CassetteModel
from agent_zero.llm.events import text_events
from agent_zero.llm.models import CallKind
from agent_zero.llm.schemas import CallUsage
from agent_zero.llm.usage import usage_from_event
from tests.llm.streams import PROMPT, Verdict, drain, output_of, text_of


def stream_entry(role: str, text: str) -> CassetteEntry:
    return CassetteEntry(
        role=role,
        kind=CallKind.STREAM,
        model_id="claude-haiku-5-5",
        events=[dict(event) for event in text_events(text)],
    )


async def test_replays_only_entries_of_its_role() -> None:
    model = CassetteModel([stream_entry("victim", "a"), stream_entry("prober", "b")], "prober")

    assert text_of(await drain(model.stream(PROMPT))) == "b"
    assert model.get_config()["model_id"] == "claude-haiku-5-5"
    assert model.remaining() == 0


async def test_structured_entries_are_keyed_by_output_model() -> None:
    entry = CassetteEntry(
        role="analyzer",
        kind=CallKind.STRUCTURED,
        output_model="Verdict",
        payload={"label": "violación"},
        usage=CallUsage(input_tokens=9),
    )
    model = CassetteModel([entry], "analyzer")

    events = await drain(model.structured_output(Verdict, PROMPT))

    assert output_of(events) == Verdict(label="violación")
    assert any(usage_from_event(event) == CallUsage(input_tokens=9) for event in events)


async def test_exhausted_cassette_names_the_missing_call() -> None:
    model = CassetteModel([], "patcher")

    with pytest.raises(CassetteExhaustedError, match=r"patcher.*Verdict"):
        await drain(model.structured_output(Verdict, PROMPT))
