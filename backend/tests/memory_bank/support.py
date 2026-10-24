from agent_zero.identity.schemas import AgentPrincipal
from agent_zero.memory_bank.memory_access import require_scope


class ScopeOnlyGuard:
    async def authorize(self, principal: AgentPrincipal, scope: str) -> AgentPrincipal:
        require_scope(principal, scope)
        return principal
