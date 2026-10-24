from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from agent_zero.agent_gateway.business_policy import CallContext
from agent_zero.agent_gateway.errors import DuplicateToolError
from agent_zero.agent_gateway.schemas import ToolSpec
from agent_zero.identity.schemas import AgentPrincipal

ToolHandler = Callable[[dict[str, Any]], Awaitable[str]]
ContextualToolHandler = Callable[[dict[str, Any], CallContext, AgentPrincipal], Awaitable[str]]


@dataclass(frozen=True)
class RegisteredTool:
    spec: ToolSpec
    handler: ToolHandler
    contextual_handler: ContextualToolHandler | None = None


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, spec: ToolSpec, handler: ToolHandler) -> None:
        if spec.name in self._tools:
            raise DuplicateToolError(spec.name)
        self._tools[spec.name] = RegisteredTool(spec, handler)

    def get(self, name: str) -> RegisteredTool | None:
        return self._tools.get(name)

    def bind_contextual(self, name: str, handler: ContextualToolHandler) -> None:
        tool = self._tools[name]
        self._tools[name] = RegisteredTool(tool.spec, tool.handler, handler)

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._tools))
