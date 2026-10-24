from typing import Any, cast

from strands.types.streaming import StreamEvent

from agent_zero.llm.schemas import CallUsage
from agent_zero.llm.usage import usage_metadata


def text_events(
    text: str, stop_reason: str = "end_turn", usage: CallUsage | None = None
) -> list[StreamEvent]:
    events: list[StreamEvent] = [
        {"messageStart": {"role": "assistant"}},
        {"contentBlockStart": {"start": {}}},
        {"contentBlockDelta": {"delta": {"text": text}}},
        {"contentBlockStop": {}},
        {"messageStop": {"stopReason": cast(Any, stop_reason)}},
    ]
    if usage is not None:
        events.append(cast(StreamEvent, usage_metadata(usage)))
    return events


def structured_events(stop_reason: str, usage: CallUsage | None) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = [{"event": {"messageStop": {"stopReason": stop_reason}}}]
    if usage is not None:
        events.append({"event": usage_metadata(usage)})
    return events
