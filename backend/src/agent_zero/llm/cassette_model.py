from collections import defaultdict, deque
from collections.abc import AsyncGenerator, AsyncIterator, Iterable
from typing import Any, TypeVar, cast

from pydantic import BaseModel
from strands.models.model import Model
from strands.types.content import Messages
from strands.types.streaming import StreamEvent
from strands.types.tools import ToolSpec

from agent_zero.llm.cassette import CassetteEntry
from agent_zero.llm.events import structured_events
from agent_zero.llm.models import CallKind, CallOrigin

T = TypeVar("T", bound=BaseModel)

CassetteKey = tuple[CallKind, str | None]


class CassetteExhaustedError(RuntimeError):
    pass


class CassetteModel(Model):
    def __init__(self, entries: Iterable[CassetteEntry], role: str) -> None:
        self.evidence_origin = CallOrigin.REPLAYED
        self.role = role
        self._queues: dict[CassetteKey, deque[CassetteEntry]] = defaultdict(deque)
        self._config: dict[str, Any] = {}
        self._calls: defaultdict[CassetteKey, int] = defaultdict(int)
        for entry in entries:
            if entry.role != role:
                continue
            self._queues[(entry.kind, entry.output_model)].append(entry)
            if entry.model_id and "model_id" not in self._config:
                self._config["model_id"] = entry.model_id

    def update_config(self, **model_config: Any) -> None:
        self._config.update(model_config)

    def get_config(self) -> dict[str, Any]:
        return self._config

    def remaining(self) -> int:
        return sum(len(queue) for queue in self._queues.values())

    def _take(self, kind: CallKind, output_model: str | None) -> CassetteEntry:
        key = (kind, output_model)
        self._calls[key] += 1
        queue = self._queues[key]
        if not queue:
            raise CassetteExhaustedError(
                f"la cassette del rol {self.role} no tiene más entradas {kind.value} "
                f"para {output_model or 'texto'}: llamada {self._calls[key]}"
            )
        return queue.popleft()

    async def stream(
        self,
        messages: Messages,
        tool_specs: list[ToolSpec] | None = None,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamEvent]:
        for event in self._take(CallKind.STREAM, None).events:
            yield cast(StreamEvent, event)

    async def structured_output(
        self,
        output_model: type[T],
        prompt: Messages,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[dict[str, T | Any], None]:
        entry = self._take(CallKind.STRUCTURED, output_model.__name__)
        for event in structured_events(entry.stop_reason or "end_turn", entry.usage):
            yield event
        yield {"output": output_model.model_validate(entry.payload)}
