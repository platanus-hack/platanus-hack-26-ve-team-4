from pathlib import Path

import pytest

from agent_zero.config import Settings
from agent_zero.telemetry import attributes
from agent_zero.telemetry.otel_setup import Telemetry, build_telemetry
from agent_zero.telemetry.spans import traced_span


def _memory(tmp_path: Path) -> Telemetry:
    return build_telemetry(Settings(data_dir=tmp_path, otel_exporter="memory"))


@pytest.mark.requirement("OBS-01")
def test_nested_spans_share_trace_id(tmp_path: Path) -> None:
    telemetry = _memory(tmp_path)
    run = traced_span(telemetry.tracer, "agent_zero.run", {attributes.RUN_ID: "r1"})
    step = traced_span(telemetry.tracer, "agent_zero.step", {attributes.STEP: 1})
    gate = traced_span(telemetry.tracer, "agent_zero.gateway", {attributes.DECISION: "allow"})
    with run, step, gate:
        pass
    assert telemetry.memory_exporter is not None
    spans = telemetry.memory_exporter.get_finished_spans()
    assert len(spans) == 3
    assert len({s.context.trace_id for s in spans}) == 1
    by_name = {s.name: s for s in spans}
    gateway_parent = by_name["agent_zero.gateway"].parent
    step_parent = by_name["agent_zero.step"].parent
    assert gateway_parent is not None
    assert step_parent is not None
    assert step_parent.span_id == by_name["agent_zero.run"].context.span_id
    assert gateway_parent.span_id == by_name["agent_zero.step"].context.span_id
    telemetry.shutdown()


@pytest.mark.requirement("OBS-01")
def test_keys_and_names_get_namespace(tmp_path: Path) -> None:
    telemetry = _memory(tmp_path)
    with traced_span(telemetry.tracer, "run", {"run_id": "r1"}) as span:
        span.set("agent_zero.agent_id", "a1")
    assert telemetry.memory_exporter is not None
    finished = telemetry.memory_exporter.get_finished_spans()[0]
    assert finished.name == "agent_zero.run"
    assert finished.attributes is not None
    assert finished.attributes["agent_zero.run_id"] == "r1"
    assert finished.attributes["agent_zero.agent_id"] == "a1"
    telemetry.shutdown()


@pytest.mark.requirement("OBS-03")
def test_redactor_cleans_email_in_every_string_attribute(tmp_path: Path) -> None:
    telemetry = _memory(tmp_path)
    email = "ana@example.com"

    def redact(text: str) -> str:
        return text.replace(email, "[correo]")

    with traced_span(
        telemetry.tracer, "run", {"note": f"hola {email}", "step": 2}, redact=redact
    ) as span:
        span.set("later", f"otra vez {email}")
    assert telemetry.memory_exporter is not None
    finished = telemetry.memory_exporter.get_finished_spans()[0]
    assert finished.attributes is not None
    assert all(email not in str(v) for v in finished.attributes.values())
    assert finished.attributes["agent_zero.note"] == "hola [correo]"
    assert finished.attributes["agent_zero.step"] == 2
    telemetry.shutdown()
