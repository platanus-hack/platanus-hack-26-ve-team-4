from pathlib import Path

import pytest
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from agent_zero.config import Settings
from agent_zero.telemetry.errors import TelemetryConfigError
from agent_zero.telemetry.otel_setup import build_telemetry


def _settings(tmp_path: Path, **overrides: object) -> Settings:
    return Settings.model_validate({"data_dir": tmp_path, **overrides})


@pytest.mark.requirement("OBS-03")
def test_none_exporter_has_no_memory_exporter(tmp_path: Path) -> None:
    telemetry = build_telemetry(_settings(tmp_path, otel_exporter="none"))
    assert telemetry.memory_exporter is None
    telemetry.shutdown()


@pytest.mark.requirement("OBS-03")
def test_memory_exporter_collects_spans(tmp_path: Path) -> None:
    telemetry = build_telemetry(_settings(tmp_path, otel_exporter="memory"))
    with telemetry.tracer.start_as_current_span("x"):
        pass
    assert telemetry.memory_exporter is not None
    assert len(telemetry.memory_exporter.get_finished_spans()) == 1
    telemetry.shutdown()


@pytest.mark.requirement("OBS-03")
def test_service_name_goes_to_resource(tmp_path: Path) -> None:
    telemetry = build_telemetry(
        _settings(tmp_path, otel_exporter="memory", otel_service_name="svc")
    )
    with telemetry.tracer.start_as_current_span("x"):
        pass
    assert telemetry.memory_exporter is not None
    span = telemetry.memory_exporter.get_finished_spans()[0]
    assert span.resource.attributes["service.name"] == "svc"
    telemetry.shutdown()


@pytest.mark.requirement("OBS-03")
def test_console_exporter_builds(tmp_path: Path) -> None:
    telemetry = build_telemetry(_settings(tmp_path, otel_exporter="console"))
    assert telemetry.memory_exporter is None
    telemetry.shutdown()


@pytest.mark.requirement("OBS-03")
def test_otlp_exporter_builds_http_exporter(tmp_path: Path) -> None:
    telemetry = build_telemetry(
        _settings(tmp_path, otel_exporter="otlp", otel_endpoint="http://localhost:4318/v1/traces")
    )
    processors = telemetry.provider._active_span_processor._span_processors
    assert any(
        isinstance(p, BatchSpanProcessor) and isinstance(p.span_exporter, OTLPSpanExporter)
        for p in processors
    )
    telemetry.shutdown()


@pytest.mark.requirement("OBS-03")
def test_otlp_without_endpoint_fails_clearly(tmp_path: Path) -> None:
    with pytest.raises(TelemetryConfigError, match="OTEL_ENDPOINT"):
        build_telemetry(_settings(tmp_path, otel_exporter="otlp"))
