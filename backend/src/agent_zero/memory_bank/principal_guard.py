from typing import Protocol

from agent_zero.identity.schemas import AgentPrincipal


class PrincipalGuard(Protocol):
    async def authorize(self, principal: AgentPrincipal, scope: str) -> AgentPrincipal: ...
