from enum import StrEnum


class GatewayDecision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    REDACT = "redact"


class GatewayStage(StrEnum):
    IDENTITY = "identity"
    POLICY = "policy"
    INPUT_ARMOR = "input_armor"
    TOOL = "tool"
    OUTPUT_ARMOR = "output_armor"
    AUDIT = "audit"


class GatewayReason(StrEnum):
    OK = "ok"
    INPUT_PII_REDACTED = "input_pii_redacted"
    OUTPUT_PII_REDACTED = "output_pii_redacted"
    IDENTITY_MALFORMED = "identity_malformed"
    IDENTITY_BAD_SIGNATURE = "identity_bad_signature"
    IDENTITY_EXPIRED = "identity_expired"
    IDENTITY_REVOKED = "identity_revoked"
    IDENTITY_MISSING_SCOPE = "identity_missing_scope"
    AGENT_NOT_APPROVED = "agent_not_approved"
    TOOL_UNREGISTERED = "tool_unregistered"
    TOOL_NOT_IN_MANIFEST = "tool_not_in_manifest"
    CLASSIFICATION_EXCEEDS_CLEARANCE = "classification_exceeds_clearance"
    REGION_NOT_ALLOWED_FOR_AGENT = "region_not_allowed_for_agent"
    REGION_NOT_ALLOWED_BY_POLICY = "region_not_allowed_by_policy"
    RATE_LIMITED = "rate_limited"
    INPUT_BLOCKED = "input_blocked"
    OUTPUT_BLOCKED = "output_blocked"
    TOOL_FAILED = "tool_failed"
