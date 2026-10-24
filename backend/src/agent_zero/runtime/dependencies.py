from collections.abc import Callable
from datetime import datetime
from typing import Annotated

from fastapi import Depends, Request

from agent_zero.runtime.handler_registry import HandlerRegistry
from agent_zero.shared.clock import utc_now


def get_handler_registry(request: Request) -> HandlerRegistry:
    registry: HandlerRegistry = request.app.state.handler_registry
    return registry


def get_runtime_clock(request: Request) -> Callable[[], datetime]:
    clock: Callable[[], datetime] = getattr(request.app.state, "runtime_clock", utc_now)
    return clock


Registry = Annotated[HandlerRegistry, Depends(get_handler_registry)]
RuntimeClock = Annotated[Callable[[], datetime], Depends(get_runtime_clock)]
