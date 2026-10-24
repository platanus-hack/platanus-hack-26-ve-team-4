from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
    SpanExporter,
)
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import Tracer

from agent_zero.config import Settings
from agent_zero.telemetry.errors import TelemetryConfigError


class Telemetry:
    def __init__(
        self,
        provider: TracerProvider,
        memory_exporter: InMemorySpanExporter | None = None,
    ) -> None:
        self.provider = provider
        self.memory_exporter = memory_exporter
        self.tracer: Tracer = provider.get_tracer("agent_zero")

    def shutdown(self) -> None:
        self.provider.shutdown()


def build_telemetry(settings: Settings) -> Telemetry:
    resource = Resource.create({"service.name": settings.otel_service_name})
    provider = TracerProvider(resource=resource)
    memory_exporter: InMemorySpanExporter | None = None
    match settings.otel_exporter:
        case "none":
            pass
        case "memory":
            memory_exporter = InMemorySpanExporter()
            provider.add_span_processor(SimpleSpanProcessor(memory_exporter))
        case "console":
            provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
        case "otlp":
            provider.add_span_processor(BatchSpanProcessor(_otlp_exporter(settings)))
    return Telemetry(provider, memory_exporter)


def _otlp_exporter(settings: Settings) -> SpanExporter:
    if not settings.otel_endpoint:
        raise TelemetryConfigError(
            "El exportador otlp requiere AGENT_ZERO_OTEL_ENDPOINT con la URL del colector."
        )
    return OTLPSpanExporter(endpoint=settings.otel_endpoint)
