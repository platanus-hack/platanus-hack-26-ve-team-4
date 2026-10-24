import base64
import binascii
import codecs
import re
from urllib.parse import unquote

from agent_zero.armor.hidden_text import decode_tag_characters

MIN_DECODED_CHARS = 8
MIN_TEXT_RATIO = 0.75
BASE64_TOKEN = re.compile(r"[A-Za-z0-9+/]{16,}={0,2}")
HEX_TOKEN = re.compile(r"(?:[0-9a-fA-F]{2}){8,}")
MAX_DECODE_DEPTH = 4
MAX_CANDIDATES = 48
PERCENT_ESCAPE = re.compile(r"%[0-9A-Fa-f]{2}")


def looks_like_text(value: str) -> bool:
    if len(value) < MIN_DECODED_CHARS or not value.isprintable():
        return False
    readable = sum(1 for char in value if char.isalpha() or char.isspace())
    return readable >= MIN_TEXT_RATIO * len(value)


def decode_base64_token(candidate: str) -> str | None:
    token = candidate.rstrip("=")
    padding = -len(token) % 4
    if padding == 3:
        return None
    try:
        raw = base64.b64decode(token + "=" * padding, validate=True).decode("utf-8")
    except (binascii.Error, ValueError, UnicodeDecodeError):
        return None
    return raw if looks_like_text(raw) else None


def decode_base64_tokens(text: str) -> list[str]:
    decoded = (decode_base64_token(match.group(0)) for match in BASE64_TOKEN.finditer(text))
    return [item for item in decoded if item is not None]


def rot13(text: str) -> str:
    return codecs.decode(text, "rot13")


def decode_percent(text: str) -> str | None:
    if not PERCENT_ESCAPE.search(text):
        return None
    decoded = unquote(text)
    return decoded if decoded != text else None


def decode_hex_tokens(text: str) -> list[str]:
    decoded: list[str] = []
    for match in HEX_TOKEN.finditer(text):
        try:
            raw = bytes.fromhex(match.group(0)).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            continue
        if looks_like_text(raw):
            decoded.append(raw)
    return decoded


def _children(text: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = [("rot13", rot13(text))]
    found.extend(("base64", item) for item in decode_base64_tokens(text))
    found.extend(("hex", item) for item in decode_hex_tokens(text))
    percent = decode_percent(text)
    if percent is not None:
        found.append(("url", percent))
    tags = decode_tag_characters(text)
    if tags is not None:
        found.append(("etiquetas", tags))
    return found


def decoded_candidates(text: str) -> tuple[tuple[str, str], ...]:
    seen = {text}
    results: list[tuple[str, str]] = []
    frontier: list[tuple[str, str]] = [("", text)]
    for _ in range(MAX_DECODE_DEPTH):
        following: list[tuple[str, str]] = []
        for chain, current in frontier:
            for technique, value in _children(current):
                if value in seen or len(results) >= MAX_CANDIDATES:
                    continue
                seen.add(value)
                label = f"{chain}+{technique}" if chain else technique
                results.append((label, value))
                following.append((label, value))
        frontier = following
    return tuple(results)
