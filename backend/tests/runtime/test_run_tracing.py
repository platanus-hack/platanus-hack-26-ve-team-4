from pathlib import Path

from agent_zero.config import Settings
from agent_zero.runtime.run_tracing import current_trace_id, run_span
from agent_zero.telemetry.otel_setup import build_telemetry


def test_no_telemetry_yields_none() -> None:
    with run_span(None, "runtime.run", "r", "a") as span:
        assert span is None
        assert current_trace_id(span) is None


def test_span_carries_run_id(tmp_path: Path) -> None:
    telemetry = build_telemetry(Settings(data_dir=tmp_path, otel_exporter="memory"))
    with run_span(telemetry, "runtime.step", "run-1", "agente", 2) as span:
        assert current_trace_id(span) is not None
    assert telemetry.memory_exporter is not None
    finished = telemetry.memory_exporter.get_finished_spans()
    assert finished[0].name == "agent_zero.runtime.step"
    assert finished[0].attributes is not None
    assert finished[0].attributes["agent_zero.run_id"] == "run-1"
    assert finished[0].attributes["agent_zero.step"] == 2
