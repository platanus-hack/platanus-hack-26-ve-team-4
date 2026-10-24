from collections.abc import AsyncIterable
from typing import Any

from pydantic import BaseModel
from strands.types.content import Messages

PROMPT: Messages = [{"role": "user", "content": [{"text": "hola"}]}]


class Verdict(BaseModel):
    label: str


async def drain[T](events: AsyncIterable[T]) -> list[T]:
    return [event async for event in events]


def text_of(events: list[Any]) -> str:
    return "".join(
        event["contentBlockDelta"]["delta"].get("text", "")
        for event in events
        if "contentBlockDelta" in event
    )


def output_of(events: list[Any]) -> Any:
    return next(event["output"] for event in events if "output" in event)
