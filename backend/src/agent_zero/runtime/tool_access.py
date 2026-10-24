from typing import Any, Protocol

from agent_zero.identity.schemas import AgentPrincipal


class ToolAccess(Protocol):
    async def call_tool(
        self, tool_name: str, arguments: dict[str, Any], data_region: str | None = None
    ) -> str: ...


class ToolAccessProvider(Protocol):
    def tools_for(self, principal: AgentPrincipal) -> ToolAccess: ...
