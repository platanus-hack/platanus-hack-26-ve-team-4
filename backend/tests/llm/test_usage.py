from agent_zero.llm.schemas import CallUsage
from agent_zero.llm.usage import stop_reason_from_event, usage_from_event, usage_metadata


def test_usage_round_trips_through_strands_metadata() -> None:
    usage = CallUsage(input_tokens=12, output_tokens=7, cache_read_tokens=3, cache_write_tokens=2)

    assert usage_from_event(usage_metadata(usage)) == usage


def test_usage_is_read_inside_processed_stream_wrappers() -> None:
    event = {"event": usage_metadata(CallUsage(input_tokens=5))}

    assert usage_from_event(event) == CallUsage(input_tokens=5)


def test_events_without_usage_return_none() -> None:
    assert usage_from_event({"contentBlockDelta": {"delta": {"text": "hola"}}}) is None
    assert usage_from_event({"metadata": {"usage": {"other": 1}}}) is None


def test_stop_reason_is_extracted_from_message_stop() -> None:
    assert stop_reason_from_event({"messageStop": {"stopReason": "refusal"}}) == "refusal"
    assert stop_reason_from_event({"event": {"messageStop": {"stopReason": "end_turn"}}}) == (
        "end_turn"
    )
    assert stop_reason_from_event({"messageStart": {"role": "assistant"}}) is None
