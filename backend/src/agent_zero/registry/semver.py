import re
from typing import NamedTuple

SEMVER_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*)?$"
)


class SemverKey(NamedTuple):
    major: int
    minor: int
    patch: int
    is_release: bool
    prerelease: tuple[tuple[int, int, str], ...]


def _identifier(part: str) -> tuple[int, int, str]:
    if part.isdigit():
        return (0, int(part), "")
    return (1, 0, part)


def semver_key(version: str) -> SemverKey:
    match = SEMVER_PATTERN.fullmatch(version)
    if match is None:
        raise ValueError(f"Versión semver inválida: {version}")
    major, minor, patch, prerelease = match.groups()
    identifiers = tuple(_identifier(p) for p in prerelease.split(".")) if prerelease else ()
    return SemverKey(int(major), int(minor), int(patch), prerelease is None, identifiers)
