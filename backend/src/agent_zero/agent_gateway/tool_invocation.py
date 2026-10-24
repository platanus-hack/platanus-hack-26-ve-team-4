from typing import Any

from agent_zero.agent_gateway.business_policy import CallContext
from agent_zero.agent_gateway.errors import ToolExecutionError
from agent_zero.agent_gateway.stage_tracer import StageTracer
from agent_zero.agent_gateway.tool_registry import RegisteredTool
from agent_zero.identity.schemas import AgentPrincipal
from agent_zero.telemetry import attributes


async def invoke_tool(
    tool: RegisteredTool,
    arguments: dict[str, Any],
    context: CallContext | None,
    principal: AgentPrincipal,
    tracer: StageTracer,
) -> str:
    failure: Exception | None = None
    output = ""
    with tracer.span("tool", {attributes.TOOL: tool.spec.name}):
        try:
            if context is not None and tool.contextual_handler is not None:
                output = await tool.contextual_handler(arguments, context, principal)
            else:
                output = await tool.handler(arguments)
        except Exception as error:
            failure = error
    if failure is not None:
        raise ToolExecutionError(failure)
    return output
