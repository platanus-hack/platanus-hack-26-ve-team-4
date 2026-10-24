from collections import deque
from collections.abc import AsyncGenerator, AsyncIterator
from typing import Any, TypeVar

from pydantic import BaseModel
from strands.models.model import Model
from strands.types.content import Messages
from strands.types.streaming import StreamEvent
from strands.types.tools import ToolSpec

from agent_zero.llm.events import structured_events, text_events
from agent_zero.llm.models import CallKind, CallOrigin
from agent_zero.llm.schemas import CallUsage
from agent_zero.llm.usage import REFUSAL

T = TypeVar("T", bound=BaseModel)


class Refusal:
    pass


ScriptEntry = str | BaseModel | dict[str, Any] | list[StreamEvent] | Exception | Refusal


class PlaybackExhaustedError(RuntimeError):
    pass


class PlaybackModel(Model):
    def __init__(
        self,
        script: list[ScriptEntry] | None = None,
        model_id: str = "playback",
        usage: CallUsage | None = None,
    ) -> None:
        self.evidence_origin = CallOrigin.SIMULATED
        self._script: deque[ScriptEntry] = deque(script or [])
        self._config: dict[str, Any] = {"model_id": model_id}
        self._usage = usage
        self.calls: list[dict[str, Any]] = []

    def enqueue(self, entry: ScriptEntry) -> None:
        self._script.append(entry)

    def update_config(self, **model_config: Any) -> None:
        self._config.update(model_config)

    def get_config(self) -> dict[str, Any]:
        return self._config

    def _next(self, kind: CallKind, messages: Messages, system_prompt: str | None) -> ScriptEntry:
        self.calls.append({"kind": kind, "messages": messages, "system_prompt": system_prompt})
        if not self._script:
            raise PlaybackExhaustedError(
                f"el guion está vacío: llamada {kind.value} número {len(self.calls)} no prevista"
            )
        entry = self._script.popleft()
        if isinstance(entry, Exception):
            raise entry
        return entry

    async def stream(
        self,
        messages: Messages,
        tool_specs: list[ToolSpec] | None = None,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamEvent]:
        entry = self._next(CallKind.STREAM, messages, system_prompt)
        if isinstance(entry, Refusal):
            events = text_events("", REFUSAL, self._usage)
        elif isinstance(entry, str):
            events = text_events(entry, usage=self._usage)
        elif isinstance(entry, list):
            events = entry
        else:
            raise PlaybackExhaustedError(f"entrada de stream inválida: {type(entry).__name__}")
        for event in events:
            yield event

    async def structured_output(
        self,
        output_model: type[T],
        prompt: Messages,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[dict[str, T | Any], None]:
        entry = self._next(CallKind.STRUCTURED, prompt, system_prompt)
        if isinstance(entry, Refusal):
            for event in structured_events(REFUSAL, self._usage):
                yield event
            raise ValueError(f'Model returned stop_reason: {REFUSAL} instead of "tool_use".')
        for event in structured_events("end_turn", self._usage):
            yield event
        if isinstance(entry, output_model):
            yield {"output": entry}
        elif isinstance(entry, dict):
            yield {"output": output_model.model_validate(entry)}
        else:
            raise PlaybackExhaustedError(
                f"entrada estructurada inválida para {output_model.__name__}: "
                f"{type(entry).__name__}"
            )
