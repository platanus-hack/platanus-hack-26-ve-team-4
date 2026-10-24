from dataclasses import dataclass, field
from typing import Any

from agent_zero.agent_gateway.models import GatewayDecision, GatewayReason
from agent_zero.identity.schemas import AgentPrincipal
from agent_zero.telemetry.attributes import Redactor
from agent_zero.telemetry.audit_log import AuditLog
from agent_zero.telemetry.audit_schemas import AuditDecision, AuditEvent

ANONYMOUS_ACTOR = "desconocido"
MAX_RESOURCE_LENGTH = 120


@dataclass(frozen=True)
class GatewayOutcome:
    decision: GatewayDecision
    reason: GatewayReason
    details: dict[str, Any] = field(default_factory=dict)
    failed: bool = False


class GatewayAuditor:
    def __init__(self, audit: AuditLog, redact: Redactor) -> None:
        self._audit = audit
        self._redact = redact

    def record(
        self, principal: AgentPrincipal | None, tool_name: str, outcome: GatewayOutcome
    ) -> None:
        attributes = {
            "gateway_decision": outcome.decision.value,
            **{key: self._clean(value) for key, value in outcome.details.items()},
        }
        if principal is not None:
            attributes.update(
                agent_version=principal.version, credential_id=principal.credential_id
            )
        resource = self._redact(tool_name)[:MAX_RESOURCE_LENGTH]
        self._audit.append(
            AuditEvent(
                actor=principal.agent_id if principal else ANONYMOUS_ACTOR,
                action="gateway.call_tool",
                resource=f"tool:{resource}",
                decision=_audit_decision(outcome),
                reason=outcome.reason.value,
                attributes=attributes,
            )
        )

    def _clean(self, value: Any) -> Any:
        if isinstance(value, str):
            return self._redact(value)[:MAX_RESOURCE_LENGTH]
        if isinstance(value, list | tuple):
            return [self._clean(item) for item in value]
        if isinstance(value, dict):
            return {str(key): self._clean(item) for key, item in value.items()}
        return value


def _audit_decision(outcome: GatewayOutcome) -> AuditDecision:
    if outcome.failed:
        return AuditDecision.ERROR
    if outcome.decision is GatewayDecision.DENY:
        return AuditDecision.DENY
    return AuditDecision.ALLOW
