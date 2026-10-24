from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from agent_zero.agent_gateway.errors import DuplicateToolError
from agent_zero.agent_gateway.schemas import ToolSpec

ToolHandler = Callable[[dict[str, Any]], Awaitable[str]]


@dataclass(frozen=True)
class RegisteredTool:
    spec: ToolSpec
    handler: ToolHandler


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, spec: ToolSpec, handler: ToolHandler) -> None:
        if spec.name in self._tools:
            raise DuplicateToolError(spec.name)
        self._tools[spec.name] = RegisteredTool(spec, handler)

    def get(self, name: str) -> RegisteredTool | None:
        return self._tools.get(name)

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._tools))
