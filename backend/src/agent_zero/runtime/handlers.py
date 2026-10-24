from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from agent_zero.identity.schemas import AgentPrincipal
from agent_zero.runtime.step_results import StepResult
from agent_zero.runtime.tool_access import ToolAccess


@dataclass(frozen=True)
class StepContext:
    run_id: str
    input: dict[str, Any]
    checkpoint: dict[str, Any]
    step_index: int
    principal: AgentPrincipal
    now: datetime
    tools: ToolAccess | None = None


class RunHandler(Protocol):
    name: str

    async def step(self, context: StepContext) -> StepResult: ...
