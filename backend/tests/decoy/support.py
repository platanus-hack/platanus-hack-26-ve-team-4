from collections.abc import AsyncIterator
from typing import Any

from strands.types.content import Messages
from strands.types.streaming import StreamEvent
from strands.types.tools import ToolSpec

from tests.arena.support import ScenarioPlayback, tool_events


class DecoyPlayback(ScenarioPlayback):
    def __init__(self) -> None:
        super().__init__()
        self.offered: list[frozenset[str]] = []

    async def stream(
        self,
        messages: Messages,
        tool_specs: list[ToolSpec] | None = None,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamEvent]:
        names = frozenset(spec["name"] for spec in tool_specs or [])
        self.offered.append(names)
        content = messages[-1]["content"]
        text = next((str(item["text"]) for item in reversed(content) if "text" in item), "")
        fresh = "toolResult" not in str(content)
        if fresh and "get_service_credentials" in names and "credencial" in text.casefold():
            for event in tool_events("get_service_credentials", {}):
                yield event
            return
        if fresh and "export_customer_records" in names and "exporta" in text.casefold():
            for event in tool_events("export_customer_records", {"limit": 3}):
                yield event
            return
        async for event in super().stream(messages, tool_specs, system_prompt, **kwargs):
            yield event
