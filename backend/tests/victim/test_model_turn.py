import json
from typing import Any, cast

import pytest
from strands.types.streaming import StreamEvent

from agent_zero.llm.playback_model import PlaybackModel
from agent_zero.victim.model_turn import model_turn


def start(identity: str, index: int = 0) -> dict[str, Any]:
    return {
        "contentBlockStart": {
            "contentBlockIndex": index,
            "start": {"toolUse": {"toolUseId": identity, "name": "get_order"}},
        }
    }


def delta(fragment: str, index: int = 0) -> dict[str, Any]:
    return {
        "contentBlockDelta": {"contentBlockIndex": index, "delta": {"toolUse": {"input": fragment}}}
    }


def stop(index: int = 0) -> dict[str, Any]:
    return {"contentBlockStop": {"contentBlockIndex": index}}


END = {"messageStop": {"stopReason": "tool_use"}}


async def parse(events: list[dict[str, Any]]) -> Any:
    return await model_turn(
        PlaybackModel([cast(list[StreamEvent], events)]),
        [{"role": "user", "content": [{"text": "Consulta dos pedidos."}]}],
        "Laboratorio",
    )


async def test_parallel_native_blocks_and_fragmented_json_keep_call_identity() -> None:
    turn = await parse(
        [
            start("first", 0),
            delta('{"order_id": "A-', 0),
            start("second", 1),
            delta(json.dumps({"order_id": "B-2001"}), 1),
            stop(1),
            delta('1001"}', 0),
            stop(0),
            END,
        ]
    )
    assert [(tool.id, tool.arguments) for tool in turn.tools] == [
        ("first", {"order_id": "A-1001"}),
        ("second", {"order_id": "B-2001"}),
    ]
    assert turn.message["content"][1]["toolUse"]["toolUseId"] == "second"


@pytest.mark.parametrize(
    "events",
    [
        [start("a"), delta("{}"), stop()],
        [start("a"), delta("{}"), END],
        [start("a"), delta("[]"), stop(), END],
        [start("a"), delta("{broken"), stop(), END],
        [delta("{}"), END],
        [start("a"), start("b"), delta("{}"), stop(), END],
        [start("a"), delta("{}"), stop(), start("a"), delta("{}"), stop(), END],
        [start("a"), delta("x" * 16_001), stop(), END],
        [start("a"), delta("{}"), stop(), {"messageStop": {"stopReason": "end_turn"}}],
        [{"messageStop": {"stopReason": "max_tokens"}}],
        [{"messageStop": {"stopReason": "end_turn"}}, delta("{}")],
        [END, END],
    ],
    ids=[
        "truncated-stream",
        "unfinished-block",
        "non-object-arguments",
        "invalid-json",
        "orphan-arguments",
        "overlapping-block",
        "duplicate-identities",
        "oversized-arguments",
        "contradictory-stop",
        "token-exhaustion",
        "content-after-stop",
        "duplicate-stop",
    ],
)
async def test_incomplete_or_ambiguous_stream_cannot_become_executable(
    events: list[dict[str, Any]],
) -> None:
    with pytest.raises(ValueError, match=r"."):
        await parse(events)


async def test_provider_cannot_bypass_per_turn_tool_bound() -> None:
    events = [event for index in range(9) for event in (start(str(index)), delta("{}"), stop())]
    with pytest.raises(ValueError, match="demasiadas"):
        await parse([*events, END])
