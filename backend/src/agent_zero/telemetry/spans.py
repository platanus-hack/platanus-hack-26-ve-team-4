from collections.abc import Iterator, Mapping
from contextlib import contextmanager

from opentelemetry.trace import Span, Tracer

from agent_zero.telemetry.attributes import Redactor, identity_redactor, namespaced

AttributeValue = str | bool | int | float


class SafeSpan:
    def __init__(self, span: Span, redact: Redactor) -> None:
        self.raw = span
        self._redact = redact

    def set(self, key: str, value: AttributeValue) -> None:
        clean = self._redact(value) if isinstance(value, str) else value
        self.raw.set_attribute(namespaced(key), clean)

    def set_all(self, attributes: Mapping[str, AttributeValue]) -> None:
        for key, value in attributes.items():
            self.set(key, value)


@contextmanager
def traced_span(
    tracer: Tracer,
    name: str,
    attributes: Mapping[str, AttributeValue] | None = None,
    redact: Redactor = identity_redactor,
) -> Iterator[SafeSpan]:
    with tracer.start_as_current_span(namespaced(name)) as span:
        safe = SafeSpan(span, redact)
        safe.set_all(attributes or {})
        yield safe
