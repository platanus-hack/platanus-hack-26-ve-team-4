from enum import StrEnum


class ViolationStatus(StrEnum):
    CONFIRMED = "confirmed"
    NOT_OBSERVED = "not_observed"
    INCONCLUSIVE = "inconclusive"


class FindingStatus(StrEnum):
    OPEN = "open"
    MITIGATED = "mitigated"
    REOPENED = "reopened"
