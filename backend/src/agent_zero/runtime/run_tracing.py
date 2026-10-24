from collections.abc import Iterator
from contextlib import contextmanager

from agent_zero.telemetry import attributes
from agent_zero.telemetry.otel_setup import Telemetry
from agent_zero.telemetry.spans import SafeSpan, traced_span


@contextmanager
def run_span(
    telemetry: Telemetry | None, name: str, run_id: str, agent_id: str, step: int | None = None
) -> Iterator[SafeSpan | None]:
    if telemetry is None:
        yield None
        return
    values: dict[str, str | int] = {attributes.RUN_ID: run_id, attributes.AGENT_ID: agent_id}
    if step is not None:
        values[attributes.STEP] = step
    with traced_span(telemetry.tracer, name, values) as span:
        yield span


def current_trace_id(span: SafeSpan | None) -> str | None:
    if span is None:
        return None
    context = span.raw.get_span_context()
    return format(context.trace_id, "032x") if context.is_valid else None
