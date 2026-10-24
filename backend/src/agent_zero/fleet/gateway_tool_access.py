from typing import Any

from agent_zero.agent_gateway.agent_gateway import AgentGateway
from agent_zero.fleet.token_vault import TokenVault
from agent_zero.identity.schemas import AgentPrincipal
from agent_zero.runtime.tool_access import ToolAccess


class GatewayToolAccess:
    def __init__(self, gateway: AgentGateway, token: str) -> None:
        self._gateway = gateway
        self._token = token

    async def call_tool(
        self, tool_name: str, arguments: dict[str, Any], data_region: str | None = None
    ) -> str:
        result = await self._gateway.call_tool(self._token, tool_name, arguments, data_region)
        return result.output


class GatewayToolProvider:
    def __init__(self, gateway: AgentGateway, vault: TokenVault) -> None:
        self._gateway = gateway
        self._vault = vault

    def tools_for(self, principal: AgentPrincipal) -> ToolAccess:
        return GatewayToolAccess(self._gateway, self._vault.token_for(principal.credential_id))
