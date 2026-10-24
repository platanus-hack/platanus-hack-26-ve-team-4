import hashlib
import hmac
import json
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict, ValidationError


class AnchorStore(Protocol):
    def read(self) -> str | None: ...

    def write(self, value: str) -> None: ...


class MemoryAnchor:
    def __init__(self) -> None:
        self.value: str | None = None

    def read(self) -> str | None:
        return self.value

    def write(self, value: str) -> None:
        self.value = value


class FileAnchor:
    def __init__(self, path: Path) -> None:
        self.path = path

    def read(self) -> str | None:
        if not self.path.exists():
            return None
        return self.path.read_text(encoding="utf-8").strip() or None

    def write(self, value: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(value + "\n", encoding="utf-8")
        temporary.replace(self.path)


class Anchor(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    entries: int
    last_hash: str
    mac: str


def _mac(key: bytes, entries: int, last_hash: str) -> str:
    message = f"{entries}:{last_hash}".encode()
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def sign_anchor(key: bytes, entries: int, last_hash: str) -> str:
    anchor = Anchor(entries=entries, last_hash=last_hash, mac=_mac(key, entries, last_hash))
    return json.dumps(anchor.model_dump(), sort_keys=True, separators=(",", ":"))


def anchor_matches(key: bytes, raw: str | None, entries: int, last_hash: str) -> bool:
    if raw is None:
        return False
    try:
        anchor = Anchor.model_validate_json(raw)
    except ValidationError:
        return False
    authentic = hmac.compare_digest(anchor.mac, _mac(key, anchor.entries, anchor.last_hash))
    return authentic and anchor.entries == entries and anchor.last_hash == last_hash
