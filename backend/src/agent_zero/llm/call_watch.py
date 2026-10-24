import time
from datetime import datetime
from typing import Any
from uuid import uuid4

from strands.models.anthropic import AnthropicModel
from strands.models.model import Model

from agent_zero.llm.context import declared_prompt_version
from agent_zero.llm.models import CallKind, CallOrigin, CallOutcome
from agent_zero.llm.pricing import cost_or_none
from agent_zero.llm.schemas import CallRecord, CallScope, CallUsage
from agent_zero.llm.usage import REFUSAL, stop_reason_from_event, usage_from_event

UNKNOWN_MODEL = "unknown"


def call_origin(model: Model) -> CallOrigin:
    current: Any = model
    while current is not None:
        declared = vars(current).get("evidence_origin")
        if isinstance(declared, CallOrigin):
            return declared
        if isinstance(current, AnthropicModel):
            return CallOrigin.LIVE
        current = vars(current).get("inner")
    return CallOrigin.SIMULATED


def model_id_of(model: Model) -> str:
    config = model.get_config()
    model_id = config.get("model_id") if isinstance(config, dict) else None
    return model_id if isinstance(model_id, str) and model_id else UNKNOWN_MODEL


class CallWatch:
    def __init__(
        self,
        inner: Model,
        role: str,
        kind: CallKind,
        scope: CallScope,
        output_model: str | None = None,
    ) -> None:
        self.call_id = uuid4().hex
        self.role = role
        self.kind = kind
        self.scope = scope
        self.output_model = output_model
        self.model_id = model_id_of(inner)
        self.origin = call_origin(inner)
        self.usage: CallUsage | None = None
        self.stop_reason: str | None = None
        self.latency_ms = 0.0
        self._started = time.perf_counter()

    @property
    def refused(self) -> bool:
        return self.stop_reason == REFUSAL

    def observe(self, event: Any) -> None:
        self.usage = usage_from_event(event) or self.usage
        self.stop_reason = stop_reason_from_event(event) or self.stop_reason

    def record(self, outcome: CallOutcome, at: datetime, error: str = "") -> CallRecord:
        self.latency_ms = (time.perf_counter() - self._started) * 1000
        return CallRecord(
            call_id=self.call_id,
            at=at,
            role=self.role,
            model_id=self.model_id,
            kind=self.kind,
            output_model=self.output_model,
            origin=self.origin,
            outcome=outcome,
            latency_ms=self.latency_ms,
            usage=self.usage,
            cost=None if self.usage is None else cost_or_none(self.model_id, self.usage),
            stop_reason=self.stop_reason,
            prompt_version=declared_prompt_version(),
            scope=self.scope,
            error=error,
        )
