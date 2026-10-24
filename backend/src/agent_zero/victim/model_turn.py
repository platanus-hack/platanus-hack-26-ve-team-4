from typing import Any, cast

from pydantic import BaseModel, Field
from strands.models.model import Model
from strands.types.content import Messages

from agent_zero.victim.tool_schemas import tool_specs
from agent_zero.victim.turn_accumulator import TurnAccumulator


class ProposedTool(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any]


class ModelTurn(BaseModel):
    text: str = ""
    tools: list[ProposedTool] = Field(default_factory=list)
    message: dict[str, Any]


async def model_turn(model: Model, messages: Messages, system_prompt: str) -> ModelTurn:
    accumulator = TurnAccumulator()
    async for raw in model.stream(messages, tool_specs=tool_specs(), system_prompt=system_prompt):
        accumulator.accept(cast(dict[str, Any], raw))
    proposed = [ProposedTool.model_validate(item) for item in accumulator.finish()]
    text = "".join(accumulator.text)
    content: list[dict[str, Any]] = [{"text": text}] if text else []
    content.extend(
        {"toolUse": {"toolUseId": item.id, "name": item.name, "input": item.arguments}}
        for item in proposed
    )
    return ModelTurn(
        text=text,
        tools=proposed,
        message={"role": "assistant", "content": content or [{"text": "Sin respuesta."}]},
    )
