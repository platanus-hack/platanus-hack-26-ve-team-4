from pathlib import Path

from agent_zero.llm.cassette import CassetteWriter, load_cassette
from agent_zero.llm.cassette_model import CassetteModel
from agent_zero.llm.models import CallKind, CallOrigin
from agent_zero.llm.playback_model import PlaybackModel
from agent_zero.llm.recording_model import RecordingModel
from agent_zero.llm.schemas import CallUsage
from tests.llm.streams import PROMPT, Verdict, drain, output_of, text_of


async def test_recorded_calls_replay_identically(tmp_path: Path) -> None:
    usage = CallUsage(input_tokens=5, output_tokens=2)
    inner = PlaybackModel(["hola", {"label": "ok"}], model_id="claude-haiku-5-5", usage=usage)
    recorder = RecordingModel(inner, CassetteWriter(tmp_path / "c.jsonl"), "victim")

    live_text = text_of(await drain(recorder.stream(PROMPT)))
    live_output = output_of(await drain(recorder.structured_output(Verdict, PROMPT)))

    entries = load_cassette(tmp_path / "c.jsonl")
    assert [entry.kind for entry in entries] == [CallKind.STREAM, CallKind.STRUCTURED]
    assert all(entry.usage == usage for entry in entries)
    replay = CassetteModel(entries, "victim")
    assert text_of(await drain(replay.stream(PROMPT))) == live_text
    assert output_of(await drain(replay.structured_output(Verdict, PROMPT))) == live_output


def test_recorder_keeps_the_origin_of_what_it_wraps(tmp_path: Path) -> None:
    recorder = RecordingModel(PlaybackModel(), CassetteWriter(tmp_path / "c.jsonl"), "victim")

    assert recorder.evidence_origin is CallOrigin.SIMULATED
