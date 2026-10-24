import time
from collections.abc import AsyncGenerator, AsyncIterator
from typing import Any, TypeVar

from pydantic import BaseModel
from strands.models.model import Model
from strands.types.content import Messages
from strands.types.streaming import StreamEvent
from strands.types.tools import ToolSpec

from agent_zero.llm.call_watch import call_origin, model_id_of
from agent_zero.llm.cassette import CassetteEntry, CassetteWriter
from agent_zero.llm.models import CallKind
from agent_zero.llm.schemas import CallUsage
from agent_zero.llm.usage import stop_reason_from_event, usage_from_event

T = TypeVar("T", bound=BaseModel)


class RecordingModel(Model):
    def __init__(self, inner: Model, writer: CassetteWriter, role: str) -> None:
        self.inner = inner
        self.evidence_origin = call_origin(inner)
        self._writer = writer
        self._role = role

    def update_config(self, **model_config: Any) -> None:
        self.inner.update_config(**model_config)

    def get_config(self) -> Any:
        return self.inner.get_config()

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)

    async def stream(
        self,
        messages: Messages,
        tool_specs: list[ToolSpec] | None = None,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamEvent]:
        started = time.perf_counter()
        events: list[dict[str, Any]] = []
        async for event in self.inner.stream(messages, tool_specs, system_prompt, **kwargs):
            events.append(dict(event))
            yield event
        self._write(CallKind.STREAM, started, events, events=events)

    async def structured_output(
        self,
        output_model: type[T],
        prompt: Messages,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[dict[str, T | Any], None]:
        started = time.perf_counter()
        observed: list[Any] = []
        payload: dict[str, Any] | None = None
        async for event in self.inner.structured_output(
            output_model, prompt, system_prompt=system_prompt, **kwargs
        ):
            output = event.get("output") if isinstance(event, dict) else None
            if isinstance(output, BaseModel):
                payload = output.model_dump(mode="json")
            observed.append(event)
            yield event
        if payload is not None:
            self._write(
                CallKind.STRUCTURED,
                started,
                observed,
                output_model=output_model.__name__,
                payload=payload,
            )

    def _write(self, kind: CallKind, started: float, observed: list[Any], **fields: Any) -> None:
        usage: CallUsage | None = None
        stop_reason: str | None = None
        for event in observed:
            usage = usage_from_event(event) or usage
            stop_reason = stop_reason_from_event(event) or stop_reason
        self._writer.append(
            CassetteEntry(
                role=self._role,
                kind=kind,
                model_id=model_id_of(self.inner),
                stop_reason=stop_reason,
                usage=usage,
                latency_ms=(time.perf_counter() - started) * 1000,
                **fields,
            )
        )
