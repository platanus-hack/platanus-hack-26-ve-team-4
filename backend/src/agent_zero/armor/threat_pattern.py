import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ThreatPattern:
    label: str
    regex: re.Pattern[str]


def pattern(label: str, expression: str) -> ThreatPattern:
    return ThreatPattern(label, re.compile(expression, re.MULTILINE))
