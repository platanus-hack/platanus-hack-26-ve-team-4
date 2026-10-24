import logging
from collections.abc import AsyncGenerator, AsyncIterator, Callable
from datetime import datetime
from typing import Any, NoReturn, TypeVar

from pydantic import BaseModel
from strands.models.model import Model
from strands.types.content import Messages
from strands.types.streaming import StreamEvent
from strands.types.tools import ToolSpec

from agent_zero.llm.call_watch import CallWatch
from agent_zero.llm.context import current_scope
from agent_zero.llm.errors import ModelLimitReachedError, ModelRefusedError, transient
from agent_zero.llm.ledger import CallLedger
from agent_zero.llm.limits import ModelLimits
from agent_zero.llm.models import CallKind, CallOutcome, LimitReason
from agent_zero.shared.clock import utc_now

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger("agent_zero.llm")


class InstrumentedModel(Model):
    def __init__(
        self,
        inner: Model,
        role: str,
        ledger: CallLedger,
        limits: ModelLimits | None = None,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self.inner = inner
        self.role = role
        self._ledger = ledger
        self._limits = limits
        self._clock = clock

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
        watch = self._open(CallKind.STREAM)
        try:
            async for event in self.inner.stream(messages, tool_specs, system_prompt, **kwargs):
                watch.observe(event)
                yield event
        except Exception as error:
            self._fail(watch, error)
        self._finish(watch)

    async def structured_output(
        self,
        output_model: type[T],
        prompt: Messages,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[dict[str, T | Any], None]:
        watch = self._open(CallKind.STRUCTURED, output_model.__name__)
        try:
            async for event in self.inner.structured_output(
                output_model, prompt, system_prompt=system_prompt, **kwargs
            ):
                watch.observe(event)
                yield event
        except Exception as error:
            self._fail(watch, error)
        self._finish(watch)

    def _open(self, kind: CallKind, output_model: str | None = None) -> CallWatch:
        watch = CallWatch(self.inner, self.role, kind, current_scope(), output_model)
        if self._limits is None:
            return watch
        try:
            self._limits.before(self.role, watch.scope)
        except ModelLimitReachedError as denial:
            self._close(watch, CallOutcome.DENIED, denial.reason.value)
            raise
        return watch

    def _fail(self, watch: CallWatch, error: Exception) -> NoReturn:
        if self._limits is not None:
            self._limits.after(self.role, watch.scope, watch.refused, watch.usage)
        if watch.refused:
            self._close(watch, CallOutcome.REFUSED, type(error).__name__)
            raise ModelRefusedError(self.role) from error
        self._close(watch, CallOutcome.FAILED, type(error).__name__)
        if transient(error):
            raise ModelLimitReachedError(
                f"el proveedor del rol {self.role} no está disponible",
                LimitReason.PROVIDER_UNAVAILABLE,
            ) from error
        raise error

    def _finish(self, watch: CallWatch) -> None:
        if self._limits is not None:
            self._limits.after(self.role, watch.scope, True, watch.usage)
        if watch.refused:
            self._close(watch, CallOutcome.REFUSED)
            raise ModelRefusedError(self.role)
        self._close(watch, CallOutcome.OK)

    def _close(self, watch: CallWatch, outcome: CallOutcome, error: str = "") -> None:
        record = watch.record(outcome, self._clock(), error)
        self._ledger.append(record)
        logger.info(
            "llm_call role=%s outcome=%s latency_ms=%.1f usd=%s",
            record.role,
            record.outcome.value,
            record.latency_ms,
            "-" if record.cost is None else f"{record.cost.total_usd:.6f}",
            extra={"llm_call": record.model_dump(mode="json")},
        )
