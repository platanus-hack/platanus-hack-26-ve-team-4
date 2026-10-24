from pathlib import Path

import pytest

from agent_zero.config import Settings
from agent_zero.llm.playback_model import PlaybackModel
from agent_zero.llm.traced_model import SPAN_NAME, TracedModel
from agent_zero.telemetry.otel_setup import Telemetry, build_telemetry
from agent_zero.telemetry.spans import traced_span
from tests.llm.streams import PROMPT, Verdict, drain


def _telemetry(tmp_path: Path) -> Telemetry:
    return build_telemetry(Settings(data_dir=tmp_path, otel_exporter="memory"))


@pytest.mark.requirement("OBS-01")
async def test_stream_emits_model_span_nested_under_current_span(tmp_path: Path) -> None:
    telemetry = _telemetry(tmp_path)
    model = TracedModel(PlaybackModel(["hola"]), "victim", telemetry.tracer)
    with traced_span(telemetry.tracer, "runtime.step"):
        await drain(model.stream(PROMPT))
    assert telemetry.memory_exporter is not None
    spans = {s.name: s for s in telemetry.memory_exporter.get_finished_spans()}
    call = spans[SPAN_NAME]
    step = spans["agent_zero.runtime.step"]
    assert call.context is not None
    assert step.context is not None
    assert call.context.trace_id == step.context.trace_id
    assert call.parent is not None
    assert call.parent.span_id == step.context.span_id
    assert call.attributes is not None
    assert call.attributes["agent_zero.model"] == "victim"
    assert call.attributes["agent_zero.call_kind"] == "stream"
    telemetry.shutdown()


@pytest.mark.requirement("OBS-01")
async def test_structured_output_emits_span(tmp_path: Path) -> None:
    telemetry = _telemetry(tmp_path)
    model = TracedModel(PlaybackModel([{"label": "ok"}]), "victim", telemetry.tracer)
    await drain(model.structured_output(Verdict, PROMPT))
    assert telemetry.memory_exporter is not None
    [span] = telemetry.memory_exporter.get_finished_spans()
    assert span.attributes is not None
    assert span.attributes["agent_zero.call_kind"] == "structured"
    telemetry.shutdown()


@pytest.mark.requirement("OBS-01")
async def test_failure_marks_span_with_error_type_only(tmp_path: Path) -> None:
    telemetry = _telemetry(tmp_path)
    model = TracedModel(PlaybackModel([TimeoutError("cliente@example.com")]), "v", telemetry.tracer)
    with pytest.raises(TimeoutError):
        await drain(model.stream(PROMPT))
    assert telemetry.memory_exporter is not None
    [span] = telemetry.memory_exporter.get_finished_spans()
    assert span.attributes is not None
    assert span.attributes["agent_zero.error_type"] == "TimeoutError"
    assert "cliente@example.com" not in str(dict(span.attributes))
    telemetry.shutdown()
