from agent_zero.llm.events import structured_events, text_events
from agent_zero.llm.schemas import CallUsage
from agent_zero.llm.usage import stop_reason_from_event, usage_from_event
from tests.llm.streams import text_of


def test_text_events_carry_text_stop_reason_and_usage() -> None:
    usage = CallUsage(input_tokens=3, output_tokens=2)

    events = text_events("hola", usage=usage)

    assert text_of(events) == "hola"
    assert [stop_reason_from_event(event) for event in events if "messageStop" in event] == [
        "end_turn"
    ]
    assert usage_from_event(events[-1]) == usage


def test_structured_events_omit_usage_when_unknown() -> None:
    events = structured_events("refusal", None)

    assert len(events) == 1
    assert stop_reason_from_event(events[0]) == "refusal"
