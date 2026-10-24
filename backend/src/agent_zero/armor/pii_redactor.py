import re
from collections.abc import Callable

from agent_zero.armor.models import PiiKind
from agent_zero.armor.pii_patterns import CARD, CEDULA, EMAIL, PHONE_PATTERNS, RUT
from agent_zero.armor.pii_validators import is_valid_rut, passes_luhn


def _substitute(
    text: str,
    regex: re.Pattern[str],
    kind: PiiKind,
    found: list[PiiKind],
    accepts: Callable[[str], bool] | None = None,
) -> str:
    def replace(match: re.Match[str]) -> str:
        if accepts is not None and not accepts(match.group(0)):
            return match.group(0)
        found.append(kind)
        return kind.tag

    return regex.sub(replace, text)


def redact_with_kinds(text: str) -> tuple[str, tuple[PiiKind, ...]]:
    found: list[PiiKind] = []
    result = _substitute(text, CARD, PiiKind.CARD, found, passes_luhn)
    result = _substitute(result, RUT, PiiKind.RUT, found, is_valid_rut)
    result = _substitute(result, CEDULA, PiiKind.CEDULA, found)
    result = _substitute(result, EMAIL, PiiKind.EMAIL, found)
    for phone in PHONE_PATTERNS:
        result = _substitute(result, phone, PiiKind.PHONE, found)
    return result, tuple(dict.fromkeys(found))
