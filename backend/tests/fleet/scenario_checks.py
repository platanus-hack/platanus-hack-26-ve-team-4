from collections.abc import Sequence

from opentelemetry.sdk.trace import ReadableSpan


def assert_model_spans_nested_in_steps(spans: Sequence[ReadableSpan]) -> None:
    by_id = {span.context.span_id: span for span in spans if span.context}
    model_spans = [s for s in spans if s.name == "agent_zero.model.call"]
    assert model_spans
    for model_span in model_spans:
        assert model_span.parent is not None
        assert by_id[model_span.parent.span_id].name == "agent_zero.runtime.step"
