import pytest

from agent_zero.agent_gateway.gateway_auditor import GatewayAuditor, GatewayOutcome
from agent_zero.agent_gateway.models import GatewayDecision, GatewayReason
from agent_zero.armor.model_armor import ModelArmor
from agent_zero.telemetry.audit_log import AuditLog
from agent_zero.telemetry.audit_schemas import AuditDecision


@pytest.mark.requirement("GW-03")
def test_records_deny_with_reason_and_redacts_the_resource() -> None:
    log = AuditLog.in_memory()
    auditor = GatewayAuditor(log, ModelArmor().redact_pii)
    outcome = GatewayOutcome(GatewayDecision.DENY, GatewayReason.RATE_LIMITED, {"stage": "policy"})
    auditor.record(None, "tool_ana@example.com", outcome)
    entry = log.entries()[0]
    assert entry.actor == "desconocido"
    assert entry.decision is AuditDecision.DENY
    assert entry.reason == "rate_limited"
    assert "ana@example.com" not in entry.resource
    assert entry.attributes == {"gateway_decision": "deny", "stage": "policy"}


@pytest.mark.requirement("GW-03")
def test_redact_maps_to_allow_and_failure_to_error() -> None:
    log = AuditLog.in_memory()
    auditor = GatewayAuditor(log, ModelArmor().redact_pii)
    auditor.record(
        None, "t", GatewayOutcome(GatewayDecision.REDACT, GatewayReason.OUTPUT_PII_REDACTED)
    )
    auditor.record(
        None, "t", GatewayOutcome(GatewayDecision.DENY, GatewayReason.TOOL_FAILED, failed=True)
    )
    first, second = log.entries()
    assert first.decision is AuditDecision.ALLOW
    assert first.attributes["gateway_decision"] == "redact"
    assert second.decision is AuditDecision.ERROR
    assert log.verify().ok


@pytest.mark.requirement("GW-03", "OBS-03")
def test_string_details_are_redacted_before_reaching_the_chain() -> None:
    log = AuditLog.in_memory()
    auditor = GatewayAuditor(log, ModelArmor().redact_pii)
    details = {"data_region": "juan@example.com", "tags": ["4111 1111 1111 1111"], "n": 3}
    auditor.record(
        None,
        "t",
        GatewayOutcome(GatewayDecision.DENY, GatewayReason.REGION_NOT_ALLOWED_FOR_AGENT, details),
    )
    entry = log.entries()[0]
    assert entry.attributes["data_region"] == "[EMAIL]"
    assert entry.attributes["tags"] == ["[CARD]"]
    assert entry.attributes["n"] == 3
