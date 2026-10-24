from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agent_zero.runtime.admission import AgentAdmission
from agent_zero.runtime.handler_registry import HandlerRegistry
from agent_zero.runtime.tool_access import ToolAccessProvider
from agent_zero.shared.clock import utc_now
from agent_zero.telemetry.otel_setup import Telemetry


@dataclass(frozen=True)
class RuntimeWiring:
    sessions: async_sessionmaker[AsyncSession]
    registry: HandlerRegistry
    admission: AgentAdmission
    clock: Callable[[], datetime] = field(default=utc_now)
    telemetry: Telemetry | None = None
    tools: ToolAccessProvider | None = None
