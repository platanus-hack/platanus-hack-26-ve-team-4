from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class CallContext:
    attempt_id: str
    session_id: str
    session_customer_id: str
    environment: str
    policy_version: int
    run_id: str
    operation_id: str = ""
    environment_id: str = ""
    campaign_id: str | None = None
    provenance: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class BusinessDenial:
    validator: str
    detail: str


class BusinessPolicy(Protocol):
    async def check(
        self, context: CallContext, tool: str, arguments: dict[str, Any]
    ) -> BusinessDenial | None: ...


class ToolObserver(Protocol):
    async def record(
        self, kind: str, context: CallContext, tool: str, data: dict[str, Any]
    ) -> None: ...


_context: ContextVar[CallContext | None] = ContextVar("tool_call_context", default=None)


def current_call_context() -> CallContext | None:
    return _context.get()


@contextmanager
def using_call_context(context: CallContext) -> Iterator[None]:
    token = _context.set(context)
    try:
        yield
    finally:
        _context.reset(token)
