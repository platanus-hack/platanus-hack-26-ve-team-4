from enum import StrEnum


class Route(StrEnum):
    PROTECTED = "protected"
    HONEYPOT = "honeypot"


class Decision(StrEnum):
    ALLOW = "allow"
    BLOCK = "block"
    DIVERT = "divert"
