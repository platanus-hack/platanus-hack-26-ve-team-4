import base64
import codecs

ZERO_WIDTH = "\u200b"
CYRILLIC_SWAPS = {"a": "\u0430", "e": "\u0435", "o": "\u043e", "p": "\u0440", "c": "\u0441"}
LEET_SWAPS = {"a": "4", "e": "3", "o": "0", "s": "5", "t": "7"}


def to_base64(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


def to_rot13(text: str) -> str:
    return codecs.encode(text, "rot13")


def with_zero_width(text: str) -> str:
    return ZERO_WIDTH.join(text)


def with_cyrillic(text: str) -> str:
    return "".join(CYRILLIC_SWAPS.get(char, char) for char in text)


def with_leet(text: str) -> str:
    return "".join(LEET_SWAPS.get(char, char) for char in text)


def with_dots(text: str) -> str:
    return " ".join(".".join(word) for word in text.split())


def with_spaced_letters(text: str) -> str:
    return "   ".join(" ".join(word) for word in text.split())


def with_fullwidth(text: str) -> str:
    return "".join(chr(ord(char) + 0xFEE0) if "!" <= char <= "~" else char for char in text)
