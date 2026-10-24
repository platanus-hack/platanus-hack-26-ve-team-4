from pathlib import Path

import pytest

from agent_zero.agent_gateway.stage_tracer import StageTracer
from agent_zero.armor.model_armor import ModelArmor
from agent_zero.config import Settings
from agent_zero.telemetry.otel_setup import build_telemetry


@pytest.mark.requirement("OBS-01", "OBS-03")
def test_stage_spans_nest_and_redact_attributes(tmp_path: Path) -> None:
    telemetry = build_telemetry(Settings(data_dir=tmp_path, otel_exporter="memory"))
    tracer = StageTracer(telemetry, ModelArmor().redact_pii)
    with tracer.span("policy", {"tool": "ana@example.com"}), tracer.span("tool"):
        pass
    assert telemetry.memory_exporter is not None
    inner, outer = telemetry.memory_exporter.get_finished_spans()
    assert outer.name == "agent_zero.gateway.policy"
    assert inner.parent is not None
    assert inner.parent.span_id == outer.context.span_id
    assert outer.attributes is not None
    assert outer.attributes["agent_zero.tool"] == "[EMAIL]"
