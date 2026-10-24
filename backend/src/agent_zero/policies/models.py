from enum import StrEnum


class PolicyStatus(StrEnum):
    CANDIDATE = "candidate"
    VALIDATING = "validating"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"


class FailureAction(StrEnum):
    BLOCK = "block"
    DIVERT = "divert"
    QUARANTINE = "quarantine"
