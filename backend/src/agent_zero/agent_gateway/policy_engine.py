from agent_zero.agent_gateway.models import GatewayReason
from agent_zero.agent_gateway.rate_limiter import RateLimiter
from agent_zero.agent_gateway.schemas import ToolSpec
from agent_zero.config import Settings
from agent_zero.identity.schemas import AgentPrincipal
from agent_zero.registry.schemas import ToolGrant


class PolicyEngine:
    def __init__(self, settings: Settings, limiter: RateLimiter) -> None:
        self._allowed_regions = frozenset(settings.allowed_data_regions)
        self._limiter = limiter

    def evaluate(
        self,
        principal: AgentPrincipal,
        spec: ToolSpec,
        grants: dict[str, ToolGrant] | None,
        data_region: str | None,
    ) -> GatewayReason | None:
        denial = self._static_denial(principal, spec, grants, data_region)
        if denial is not None:
            return denial
        if not self._limiter.allow(principal.agent_id):
            return GatewayReason.RATE_LIMITED
        return None

    def _static_denial(
        self,
        principal: AgentPrincipal,
        spec: ToolSpec,
        grants: dict[str, ToolGrant] | None,
        data_region: str | None,
    ) -> GatewayReason | None:
        if grants is None:
            return GatewayReason.AGENT_NOT_APPROVED
        grant = grants.get(spec.name)
        if grant is None:
            return GatewayReason.TOOL_NOT_IN_MANIFEST
        if not principal.clearance.covers(max(spec.classification, grant.classification)):
            return GatewayReason.CLASSIFICATION_EXCEEDS_CLEARANCE
        regions = {spec.region} | ({data_region} if data_region else set())
        if not regions <= set(principal.allowed_regions):
            return GatewayReason.REGION_NOT_ALLOWED_FOR_AGENT
        if not regions <= self._allowed_regions:
            return GatewayReason.REGION_NOT_ALLOWED_BY_POLICY
        return None
