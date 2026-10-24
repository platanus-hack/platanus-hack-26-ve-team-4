from enum import StrEnum


class EventType(StrEnum):
    ATTEMPT_QUEUED = "attempt_queued"
    ATTEMPT_STARTED = "attempt_started"
    TOOL_PROPOSED = "tool_proposed"
    TOOL_DENIED = "tool_denied"
    TOOL_COMPLETED = "tool_completed"
    ROUTE_CHANGED = "route_changed"
    ATTEMPT_EVALUATED = "attempt_evaluated"
    FINDING_OPENED = "finding_opened"
    PATCH_PROPOSED = "patch_proposed"
    PATCH_VALIDATED = "patch_validated"
    POLICY_ACTIVATED = "policy_activated"
    POLICY_ROLLED_BACK = "policy_rolled_back"


class Visibility(StrEnum):
    PUBLIC = "public"
    OPERATOR = "operator"
