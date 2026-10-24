import re
from collections.abc import Iterable
from typing import Any

NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
PRIORITY = ("user", "store", "untrusted", "memory")


def contains(text: str, value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int | float):
        return any(float(raw.replace(",", ".")) == float(value) for raw in NUMBER.findall(text))
    needle = str(value).strip().casefold()
    return bool(needle) and needle in text.casefold()


def origin(segments: Iterable[tuple[str, str]], value: Any) -> str:
    labels = {label for label, text in segments if contains(text, value)}
    return next((label for label in PRIORITY if label in labels), "model")


def label_arguments(segments: list[tuple[str, str]], arguments: dict[str, Any]) -> dict[str, str]:
    return {name: origin(segments, value) for name, value in sorted(arguments.items())}
