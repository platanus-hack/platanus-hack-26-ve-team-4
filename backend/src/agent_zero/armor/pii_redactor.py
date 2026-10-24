import re
import unicodedata
from collections.abc import Callable

from agent_zero.armor.decoding import BASE64_TOKEN, decode_base64_token
from agent_zero.armor.models import PiiKind
from agent_zero.armor.pii_patterns import CARD, CEDULA, EMAIL, PHONE_PATTERNS, RUT
from agent_zero.armor.pii_validators import is_valid_rut, passes_luhn

INVISIBLE_CATEGORIES = frozenset({"Mn", "Me", "Cf", "Cc", "Cs", "Co"})


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


def _plain_text(text: str) -> str:
    folded = unicodedata.normalize("NFKC", text)
    return "".join(
        char
        for char in folded
        if char.isspace() or unicodedata.category(char) not in INVISIBLE_CATEGORIES
    )


def _redact_plain(text: str, found: list[PiiKind]) -> str:
    result = _substitute(text, CARD, PiiKind.CARD, found, passes_luhn)
    result = _substitute(result, RUT, PiiKind.RUT, found, is_valid_rut)
    result = _substitute(result, CEDULA, PiiKind.CEDULA, found)
    result = _substitute(result, EMAIL, PiiKind.EMAIL, found)
    for phone in PHONE_PATTERNS:
        result = _substitute(result, phone, PiiKind.PHONE, found)
    return result


def _redact_encoded(text: str, found: list[PiiKind]) -> str:
    def replace(match: re.Match[str]) -> str:
        decoded = decode_base64_token(match.group(0))
        if decoded is None:
            return match.group(0)
        inner: list[PiiKind] = []
        _redact_plain(_plain_text(decoded), inner)
        if not inner:
            return match.group(0)
        found.extend(inner)
        return inner[0].tag

    return BASE64_TOKEN.sub(replace, text)


def redact_with_kinds(text: str) -> tuple[str, tuple[PiiKind, ...]]:
    found: list[PiiKind] = []
    cleaned = _plain_text(text)
    result = _redact_plain(_redact_encoded(cleaned, found), found)
    if not found:
        return text, ()
    return result, tuple(dict.fromkeys(found))
