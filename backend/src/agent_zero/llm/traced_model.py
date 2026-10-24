from collections.abc import AsyncGenerator, AsyncIterator
from typing import Any, TypeVar

from opentelemetry.trace import Span, StatusCode, Tracer
from pydantic import BaseModel
from strands.models.model import Model
from strands.types.content import Messages
from strands.types.streaming import StreamEvent
from strands.types.tools import ToolSpec

from agent_zero.telemetry import attributes
from agent_zero.telemetry.spans import SafeSpan

T = TypeVar("T", bound=BaseModel)

SPAN_NAME = "agent_zero.model.call"


class TracedModel(Model):
    def __init__(self, inner: Model, role: str, tracer: Tracer) -> None:
        self.inner = inner
        self.role = role
        self._tracer = tracer

    def update_config(self, **model_config: Any) -> None:
        self.inner.update_config(**model_config)

    def get_config(self) -> Any:
        return self.inner.get_config()

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)

    def _open(self, kind: str) -> Span:
        span = self._tracer.start_span(SPAN_NAME)
        safe = SafeSpan(span, lambda text: text)
        safe.set(attributes.MODEL, self.role)
        safe.set("call_kind", kind)
        return span

    @staticmethod
    def _close(span: Span, error: BaseException | None) -> None:
        if error is not None:
            span.set_attribute("agent_zero.error_type", type(error).__name__)
            span.set_status(StatusCode.ERROR)
        span.end()

    async def stream(
        self,
        messages: Messages,
        tool_specs: list[ToolSpec] | None = None,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamEvent]:
        span = self._open("stream")
        failure: BaseException | None = None
        try:
            async for event in self.inner.stream(messages, tool_specs, system_prompt, **kwargs):
                yield event
        except Exception as error:
            failure = error
            raise
        finally:
            self._close(span, failure)

    async def structured_output(
        self,
        output_model: type[T],
        prompt: Messages,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[dict[str, T | Any], None]:
        span = self._open("structured")
        failure: BaseException | None = None
        try:
            async for event in self.inner.structured_output(
                output_model, prompt, system_prompt=system_prompt, **kwargs
            ):
                yield event
        except Exception as error:
            failure = error
            raise
        finally:
            self._close(span, failure)
