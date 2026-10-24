import json
from typing import Any, cast

from pydantic import BaseModel, Field
from strands.models.model import Model
from strands.types.content import Messages

from agent_zero.victim.tool_schemas import tool_specs


class ProposedTool(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any]


class ModelTurn(BaseModel):
    text: str = ""
    tools: list[ProposedTool] = Field(default_factory=list)
    message: dict[str, Any]


async def model_turn(model: Model, messages: Messages, system_prompt: str) -> ModelTurn:
    text: list[str] = []
    tools: list[dict[str, Any]] = []
    current_tool: dict[str, Any] | None = None
    stop_reason = ""
    async for raw in model.stream(messages, tool_specs=tool_specs(), system_prompt=system_prompt):
        event = cast(dict[str, Any], raw)
        start = event.get("contentBlockStart", {}).get("start", {}).get("toolUse")
        if start:
            current_tool = {"id": start["toolUseId"], "name": start["name"], "input": ""}
            tools.append(current_tool)
        delta = event.get("contentBlockDelta", {}).get("delta", {})
        if "text" in delta:
            text.append(str(delta["text"]))
        if "toolUse" in delta and current_tool is not None:
            fragment = delta["toolUse"].get("input", "")
            current_tool["input"] += fragment if isinstance(fragment, str) else json.dumps(fragment)
        if "contentBlockStop" in event:
            current_tool = None
        if "messageStop" in event:
            stop_reason = str(event["messageStop"]["stopReason"])
    if stop_reason not in {"end_turn", "tool_use", "stop_sequence"}:
        raise ValueError("El modelo no terminó su turno de forma completa.")
    proposed = [
        ProposedTool(id=item["id"], name=item["name"], arguments=json.loads(item["input"] or "{}"))
        for item in tools
    ]
    if len({item.id for item in proposed}) != len(proposed):
        raise ValueError("El modelo repitió identificadores de herramientas.")
    content: list[dict[str, Any]] = [{"text": "".join(text)}] if text else []
    content.extend(
        {"toolUse": {"toolUseId": item.id, "name": item.name, "input": item.arguments}}
        for item in proposed
    )
    return ModelTurn(
        text="".join(text),
        tools=proposed,
        message={"role": "assistant", "content": content or [{"text": "Sin respuesta."}]},
    )
