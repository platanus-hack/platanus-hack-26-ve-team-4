import re
import unicodedata

INVISIBLE_CATEGORIES = frozenset({"Mn", "Me", "Cf", "Cc", "Cs", "Co"})

HOMOGLYPH_SOURCES = {
    "a": "\u0430\u03b1",
    "b": "\u0432",
    "e": "\u0435\u03b5",
    "k": "\u043a\u03ba",
    "m": "\u043c",
    "h": "\u043d\u04bb",
    "o": "\u043e\u03bf",
    "p": "\u0440\u03c1",
    "c": "\u0441",
    "t": "\u0442\u03c4",
    "y": "\u0443",
    "x": "\u0445\u03c7",
    "s": "\u0455",
    "i": "\u0456\u03b9\u0131",
    "j": "\u0458",
    "d": "\u0501",
    "l": "\u04cf",
    "g": "\u0261",
    "v": "\u03bd",
    "u": "\u03c5",
}

HOMOGLYPHS = {source: target for target, sources in HOMOGLYPH_SOURCES.items() for source in sources}

LEET_COMMON = {
    "0": "o",
    "3": "e",
    "4": "a",
    "5": "s",
    "7": "t",
    "8": "b",
    "@": "a",
    "$": "s",
    "!": "i",
}

_HOMOGLYPH_TABLE = str.maketrans({**HOMOGLYPHS, **{k.upper(): v for k, v in HOMOGLYPHS.items()}})
_LEET_AS_I = str.maketrans({**LEET_COMMON, "1": "i", "|": "i"})
_LEET_AS_L = str.maketrans({**LEET_COMMON, "1": "l", "|": "l"})
_INNER_PUNCTUATION = re.compile(r"(?<=\w)[.\-_*·'`]+(?=\w)")
_PUNCTUATION_AS_SPACE = re.compile(r"(?<=\w)[.\-_*·]+(?=\w)")
_SPACED_LETTERS = re.compile(r"(?<!\w)(?:\w[ \t]){1,}\w(?!\w)")
_WHITESPACE = re.compile(r"\s+")


def _visible(text: str) -> str:
    mapped = unicodedata.normalize("NFKD", text.translate(_HOMOGLYPH_TABLE))
    visible = "".join(
        char
        for char in mapped
        if char.isspace() or unicodedata.category(char) not in INVISIBLE_CATEGORIES
    )
    return visible.casefold()


def _collapse(text: str) -> str:
    return _WHITESPACE.sub(" ", text).strip()


def fold(text: str) -> str:
    return _collapse(_visible(text))


def strip_inner_punctuation(text: str) -> str:
    return _INNER_PUNCTUATION.sub("", text)


def punctuation_to_spaces(text: str) -> str:
    return _PUNCTUATION_AS_SPACE.sub(" ", text)


def join_spaced_letters(text: str) -> str:
    return _SPACED_LETTERS.sub(lambda match: re.sub(r"[ \t]", "", match.group(0)), text)


def leet_variants(text: str) -> tuple[str, str]:
    return text.translate(_LEET_AS_I), text.translate(_LEET_AS_L)


def text_variants(text: str) -> tuple[str, ...]:
    raw = _visible(text)
    stripped = strip_inner_punctuation(raw)
    bases = (
        raw,
        punctuation_to_spaces(raw),
        stripped,
        join_spaced_letters(raw),
        join_spaced_letters(stripped),
    )
    seen: dict[str, None] = {}
    for item in map(_collapse, bases):
        seen.setdefault(item)
        for leet in leet_variants(item):
            seen.setdefault(leet)
    return tuple(seen)
