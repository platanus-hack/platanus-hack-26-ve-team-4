from collections.abc import Iterator, Mapping
from contextlib import contextmanager

from agent_zero.telemetry.attributes import Redactor
from agent_zero.telemetry.otel_setup import Telemetry
from agent_zero.telemetry.spans import AttributeValue, SafeSpan, traced_span


class StageTracer:
    def __init__(self, telemetry: Telemetry, redact: Redactor) -> None:
        self._telemetry = telemetry
        self._redact = redact

    @contextmanager
    def span(
        self, stage: str, attributes: Mapping[str, AttributeValue] | None = None
    ) -> Iterator[SafeSpan]:
        with traced_span(
            self._telemetry.tracer, f"gateway.{stage}", attributes, self._redact
        ) as span:
            yield span
