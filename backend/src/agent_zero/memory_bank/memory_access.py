from agent_zero.identity.errors import IdentityDeniedError
from agent_zero.identity.models import IdentityDenialReason
from agent_zero.identity.schemas import AgentPrincipal

READ_SCOPE = "memory:read"
WRITE_SCOPE = "memory:write"


def require_scope(principal: AgentPrincipal, scope: str) -> None:
    if scope not in principal.scopes:
        raise IdentityDeniedError(IdentityDenialReason.MISSING_SCOPE)
