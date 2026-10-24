from typing import Any

from strands.types.content import Messages
from strands.types.streaming import StreamEvent
from strands.types.tools import ToolSpec

from agent_zero.llm.playback_model import PlaybackModel
from agent_zero.victim.model_turn import model_turn
from agent_zero.victim.tool_schemas import tool_specs

MESSAGES: Messages = [{"role": "user", "content": [{"text": "Hola"}]}]


class SpyModel(PlaybackModel):
    def __init__(self) -> None:
        super().__init__()
        self.offered: list[int] = []

    async def stream(
        self,
        messages: Messages,
        tool_specs: list[ToolSpec] | None = None,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> Any:
        self.offered.append(len(tool_specs or []))
        events: list[StreamEvent] = [
            {"messageStart": {"role": "assistant"}},
            {"messageStop": {"stopReason": "end_turn"}},
        ]
        for event in events:
            yield event


async def test_the_provider_is_offered_exactly_the_specs_of_the_role() -> None:
    model = SpyModel()

    await model_turn(model, MESSAGES, "Laboratorio", tool_specs())
    await model_turn(model, MESSAGES, "Laboratorio", tool_specs(decoy=True))

    assert model.offered == [4, 6]
