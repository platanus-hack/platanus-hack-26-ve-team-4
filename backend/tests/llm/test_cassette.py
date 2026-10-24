from pathlib import Path

import pytest
from pydantic import ValidationError

from agent_zero.llm.cassette import (
    CassetteEntry,
    CassetteFormatError,
    CassetteWriter,
    load_cassette,
)
from agent_zero.llm.models import CallKind
from agent_zero.llm.schemas import CallUsage


def test_entries_round_trip_through_the_file(tmp_path: Path) -> None:
    writer = CassetteWriter(tmp_path / "llm" / "cassette.jsonl")
    entry = CassetteEntry(
        role="prober",
        kind=CallKind.STRUCTURED,
        output_model="Verdict",
        payload={"label": "ñandú"},
        usage=CallUsage(input_tokens=4),
    )

    writer.append(entry)

    assert load_cassette(writer.path) == [entry]


def test_structured_entry_requires_payload() -> None:
    with pytest.raises(ValidationError, match="payload"):
        CassetteEntry(role="prober", kind=CallKind.STRUCTURED, output_model="Verdict")


def test_stream_entry_requires_events() -> None:
    with pytest.raises(ValidationError, match="eventos"):
        CassetteEntry(role="victim", kind=CallKind.STREAM)


def test_missing_and_corrupt_cassettes_are_reported(tmp_path: Path) -> None:
    path = tmp_path / "cassette.jsonl"
    with pytest.raises(CassetteFormatError, match="no existe"):
        load_cassette(path)

    path.write_text('{"role": ""}\n', encoding="utf-8")

    with pytest.raises(CassetteFormatError, match=r"cassette.jsonl:1"):
        load_cassette(path)
