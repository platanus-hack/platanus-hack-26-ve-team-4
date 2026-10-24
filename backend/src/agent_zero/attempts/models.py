from enum import StrEnum


class AttemptStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    EVALUATED = "evaluated"
    INCONCLUSIVE = "inconclusive"


class AttemptOutcome(StrEnum):
    CONFIRMED_VIOLATION = "confirmed_violation"
    PREVENTED = "prevented"
    NOT_ACHIEVED = "not_achieved"
    CONTAINED_HONEYPOT = "contained_honeypot"
    INCONCLUSIVE = "inconclusive"
