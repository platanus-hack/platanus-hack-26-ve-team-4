import json
import threading
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from agent_zero.llm.models import CallKind
from agent_zero.llm.schemas import CallUsage


class CassetteFormatError(ValueError):
    pass


class CassetteEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str = Field(min_length=1)
    kind: CallKind
    output_model: str | None = None
    events: list[dict[str, Any]] = []
    payload: dict[str, Any] | None = None
    model_id: str | None = None
    stop_reason: str | None = None
    usage: CallUsage | None = None
    latency_ms: float | None = Field(default=None, ge=0.0)

    @model_validator(mode="after")
    def carries_what_its_kind_needs(self) -> "CassetteEntry":
        if self.kind is CallKind.STRUCTURED and (self.output_model is None or self.payload is None):
            raise ValueError("una entrada structured_output necesita output_model y payload")
        if self.kind is CallKind.STREAM and not self.events:
            raise ValueError("una entrada stream necesita eventos")
        return self


def load_cassette(path: Path) -> list[CassetteEntry]:
    if not path.exists():
        raise CassetteFormatError(f"no existe la cassette {path}")
    entries: list[CassetteEntry] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            entries.append(CassetteEntry.model_validate_json(line))
        except ValueError as error:
            raise CassetteFormatError(f"{path}:{number}: {error}") from error
    return entries


class CassetteWriter:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, entry: CassetteEntry) -> None:
        line = json.dumps(entry.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)
        with self._lock, self.path.open("a", encoding="utf-8") as handle:
            handle.write(f"{line}\n")
