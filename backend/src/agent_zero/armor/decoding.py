import base64
import binascii
import codecs
import re
from urllib.parse import unquote

MIN_DECODED_CHARS = 8
MIN_TEXT_RATIO = 0.75
BASE64_TOKEN = re.compile(r"[A-Za-z0-9+/]{16,}={0,2}")
PERCENT_ESCAPE = re.compile(r"%[0-9A-Fa-f]{2}")


def looks_like_text(value: str) -> bool:
    if len(value) < MIN_DECODED_CHARS or not value.isprintable():
        return False
    readable = sum(1 for char in value if char.isalpha() or char.isspace())
    return readable >= MIN_TEXT_RATIO * len(value)


def decode_base64_tokens(text: str) -> list[str]:
    decoded: list[str] = []
    for match in BASE64_TOKEN.finditer(text):
        token = match.group(0).rstrip("=")
        padding = -len(token) % 4
        if padding == 3:
            continue
        try:
            raw = base64.b64decode(token + "=" * padding, validate=True).decode("utf-8")
        except (binascii.Error, ValueError, UnicodeDecodeError):
            continue
        if looks_like_text(raw):
            decoded.append(raw)
    return decoded


def rot13(text: str) -> str:
    return codecs.decode(text, "rot13")


def decode_percent(text: str) -> str | None:
    if not PERCENT_ESCAPE.search(text):
        return None
    decoded = unquote(text)
    return decoded if decoded != text else None


def decoded_candidates(text: str) -> tuple[tuple[str, str], ...]:
    candidates: list[tuple[str, str]] = []
    for item in decode_base64_tokens(text):
        candidates.append(("base64", item))
        candidates.append(("base64+rot13", rot13(item)))
    candidates.append(("rot13", rot13(text)))
    percent = decode_percent(text)
    if percent is not None:
        candidates.append(("url", percent))
    return tuple((technique, value) for technique, value in candidates if value != text)
