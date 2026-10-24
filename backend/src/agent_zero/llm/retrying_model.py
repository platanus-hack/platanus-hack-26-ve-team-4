import asyncio
import random
from collections.abc import AsyncGenerator, AsyncIterable, AsyncIterator, Awaitable, Callable
from typing import Any, TypeVar

from pydantic import BaseModel
from strands.models.model import Model
from strands.types.content import Messages
from strands.types.streaming import StreamEvent
from strands.types.tools import ToolSpec

from agent_zero.llm.errors import transient

T = TypeVar("T", bound=BaseModel)
E = TypeVar("E")

JITTER_FLOOR = 0.5


class RetryingModel(Model):
    def __init__(
        self,
        inner: Model,
        attempts: int = 4,
        backoff_seconds: float = 1.0,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        jitter: Callable[[], float] = random.random,
    ) -> None:
        if attempts < 1:
            raise ValueError("attempts debe ser al menos 1")
        self.inner = inner
        self.attempts = attempts
        self.backoff_seconds = backoff_seconds
        self.waits: list[float] = []
        self._sleep = sleep
        self._jitter = jitter

    def update_config(self, **model_config: Any) -> None:
        self.inner.update_config(**model_config)

    def get_config(self) -> Any:
        return self.inner.get_config()

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)

    def delay_before(self, attempt: int) -> float:
        return self.backoff_seconds * 2.0 ** (attempt - 1) * (JITTER_FLOOR + self._jitter())

    async def _collected(self, call: Callable[[], AsyncIterable[E]]) -> list[E]:
        for attempt in range(1, self.attempts + 1):
            try:
                return [event async for event in call()]
            except Exception as error:
                if attempt == self.attempts or not transient(error):
                    raise
                waited = self.delay_before(attempt)
                self.waits.append(waited)
                await self._sleep(waited)
        raise AssertionError("inalcanzable")

    async def stream(
        self,
        messages: Messages,
        tool_specs: list[ToolSpec] | None = None,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamEvent]:
        def call() -> AsyncIterable[StreamEvent]:
            return self.inner.stream(messages, tool_specs, system_prompt, **kwargs)

        for event in await self._collected(call):
            yield event

    async def structured_output(
        self,
        output_model: type[T],
        prompt: Messages,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[dict[str, T | Any], None]:
        def call() -> AsyncIterable[dict[str, T | Any]]:
            return self.inner.structured_output(
                output_model, prompt, system_prompt=system_prompt, **kwargs
            )

        for event in await self._collected(call):
            yield event
