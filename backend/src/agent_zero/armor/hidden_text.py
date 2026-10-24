import re

TAG_START = 0xE0000
FLAG_SEQUENCE = re.compile(r"\U0001f3f4[\U000e0020-\U000e007f]+")
TAG_RUN = re.compile(r"[\U000e0000-\U000e007f]+")
INVISIBLE_RANGES = ((0x200B, 0x200F), (0x2060, 0x2064), (0xFEFF, 0xFEFF), (0xAD, 0xAD))
ZERO_WIDTH_RUN = re.compile(
    "[" + "".join(f"{chr(low)}-{chr(high)}" for low, high in INVISIBLE_RANGES) + "]{4,}"
)


def _without_flag_sequences(text: str) -> str:
    return FLAG_SEQUENCE.sub("", text)


def has_tag_characters(text: str) -> bool:
    return TAG_RUN.search(_without_flag_sequences(text)) is not None


def has_invisible_run(text: str) -> bool:
    return ZERO_WIDTH_RUN.search(text) is not None


def decode_tag_characters(text: str) -> str | None:
    runs = TAG_RUN.findall(_without_flag_sequences(text))
    if not runs:
        return None
    letters = (chr(ord(char) - TAG_START) for run in runs for char in run)
    decoded = "".join(char for char in letters if char.isprintable() or char.isspace())
    return decoded or None
