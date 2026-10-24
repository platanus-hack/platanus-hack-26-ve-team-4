import hashlib
import json
from collections.abc import AsyncGenerator, AsyncIterator
from typing import Any, TypeVar, cast

from pydantic import BaseModel
from strands.models.model import Model
from strands.types.content import Messages
from strands.types.streaming import StreamEvent
from strands.types.tools import ToolSpec

from agent_zero.llm.demo_actions import (
    already_proposed,
    follow_untrusted,
    propose,
    result_texts,
)
from agent_zero.llm.demo_structured import structured_payload
from agent_zero.llm.events import structured_events, text_events
from agent_zero.llm.models import CallOrigin

T = TypeVar("T", bound=BaseModel)


class DemoModel(Model):
    """Executable simulated provider. No canned outcomes, invented usage or live fallback."""

    def __init__(self) -> None:
        self.evidence_origin = CallOrigin.SIMULATED
        self._config: dict[str, Any] = {"model_id": "demo-rule-engine-v1"}

    def update_config(self, **model_config: Any) -> None:
        self._config.update(model_config)

    def get_config(self) -> dict[str, Any]:
        return self._config

    async def stream(
        self,
        messages: Messages,
        tool_specs: list[ToolSpec] | None = None,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamEvent]:
        if tool_specs is None:
            context_text = next(
                (
                    str(part["text"]).removeprefix("Contexto: ")
                    for message in messages
                    for part in message["content"]
                    if "text" in part and str(part["text"]).startswith("Contexto: ")
                ),
                "{}",
            )
            context = json.loads(context_text)
            order = context.get("pedido", {})
            reply = (
                f"Pedido {order.get('order_id', '')}: {order.get('status', 'sin información')}. "
                + " ".join(str(item) for item in context.get("base_de_conocimiento", []))
            )
            for event in text_events(reply):
                yield event
            return
        texts = result_texts(messages)
        if texts:
            proposals = [
                (name, args)
                for name, args in follow_untrusted(texts)
                if not already_proposed(messages, name, args)
            ]
        else:
            message = next(
                str(part["text"]) for part in reversed(messages[-1]["content"]) if "text" in part
            )
            proposals = propose(message, frozenset(spec["name"] for spec in tool_specs))
        if not proposals:
            for event in text_events(
                "Resultado verificado de las herramientas: " + " ".join(texts)
            ):
                yield event
            return
        yield {"messageStart": {"role": "assistant"}}
        for index, (name, arguments) in enumerate(proposals):
            identity = hashlib.sha256(f"{len(messages)}:{index}:{name}".encode()).hexdigest()[:16]
            for raw_event in [
                {
                    "contentBlockStart": {
                        "contentBlockIndex": index,
                        "start": {"toolUse": {"toolUseId": identity, "name": name}},
                    }
                },
                {
                    "contentBlockDelta": {
                        "contentBlockIndex": index,
                        "delta": {"toolUse": {"input": json.dumps(arguments)}},
                    }
                },
                {"contentBlockStop": {"contentBlockIndex": index}},
            ]:
                yield cast(StreamEvent, raw_event)
        yield {"messageStop": {"stopReason": "tool_use"}}

    async def structured_output(
        self,
        output_model: type[T],
        prompt: Messages,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[dict[str, T | Any], None]:
        output = output_model.model_validate(structured_payload(output_model.__name__, prompt))
        for event in structured_events("end_turn", None):
            yield event
        yield {"output": output}
