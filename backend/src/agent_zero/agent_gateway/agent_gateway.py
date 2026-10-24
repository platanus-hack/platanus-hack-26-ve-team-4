from typing import Any

from agent_zero.agent_gateway.argument_screening import screen_arguments
from agent_zero.agent_gateway.errors import GatewayDeniedError, ToolExecutionError
from agent_zero.agent_gateway.gateway_auditor import GatewayOutcome
from agent_zero.agent_gateway.gateway_parts import GatewayParts
from agent_zero.agent_gateway.models import GatewayDecision, GatewayReason, GatewayStage
from agent_zero.agent_gateway.schemas import GatewayResult
from agent_zero.agent_gateway.tool_registry import RegisteredTool
from agent_zero.armor.models import ArmorAction, Surface
from agent_zero.identity.schemas import AgentPrincipal
from agent_zero.telemetry import attributes
from agent_zero.telemetry.spans import SafeSpan


class AgentGateway:
    def __init__(self, parts: GatewayParts) -> None:
        self._parts = parts

    async def call_tool(
        self,
        token: str,
        tool_name: str,
        arguments: dict[str, Any],
        data_region: str | None = None,
    ) -> GatewayResult:
        details: dict[str, Any] = {}
        principal: AgentPrincipal | None = None
        with self._parts.tracer.span("call_tool", {attributes.TOOL: tool_name}) as root:
            try:
                principal = await self._identity(token, tool_name)
                tool = await self._policy(principal, tool_name, data_region, details)
                result = await self._execute(tool, arguments, details)
            except GatewayDeniedError as denial:
                details["stage"] = denial.stage.value
                outcome = GatewayOutcome(GatewayDecision.DENY, denial.reason, details)
                self._finish(root, principal, tool_name, outcome)
                raise
            except ToolExecutionError as failure:
                details["stage"] = GatewayStage.TOOL.value
                outcome = GatewayOutcome(
                    GatewayDecision.DENY, GatewayReason.TOOL_FAILED, details, failed=True
                )
                self._finish(root, principal, tool_name, outcome)
                original = failure.original
            else:
                outcome = GatewayOutcome(result.decision, result.reason, details)
                self._finish(root, principal, tool_name, outcome)
                return result
        raise original

    async def _identity(self, token: str, tool_name: str) -> AgentPrincipal:
        with self._parts.tracer.span("identity"):
            return await self._parts.identity.authenticate(token, f"tool:{tool_name}")

    async def _policy(
        self,
        principal: AgentPrincipal,
        tool_name: str,
        data_region: str | None,
        details: dict[str, Any],
    ) -> RegisteredTool:
        with self._parts.tracer.span("policy", {attributes.AGENT_ID: principal.agent_id}):
            tool = self._parts.tools.get(tool_name)
            if tool is None:
                raise GatewayDeniedError(GatewayReason.TOOL_UNREGISTERED, GatewayStage.POLICY)
            grants = await self._parts.manifests.tool_grants(principal.agent_id, principal.version)
            details["data_region"] = data_region or tool.spec.region
            reason = self._parts.policy.evaluate(principal, tool.spec, grants, data_region)
            if reason is not None:
                raise GatewayDeniedError(reason, GatewayStage.POLICY)
            return tool

    async def _execute(
        self, tool: RegisteredTool, arguments: dict[str, Any], details: dict[str, Any]
    ) -> GatewayResult:
        with self._parts.tracer.span("input_armor"):
            screened = screen_arguments(self._parts.armor, arguments)
            details["input_threats"] = [kind.value for kind in screened.kinds]
            if screened.blocked:
                raise GatewayDeniedError(GatewayReason.INPUT_BLOCKED, GatewayStage.INPUT_ARMOR)
        output = await self._invoke(tool, screened.arguments)
        with self._parts.tracer.span("output_armor"):
            verdict = self._parts.armor.screen(output, Surface.TOOL_OUTPUT)
            details["output_threats"] = sorted({f.kind.value for f in verdict.findings})
            if verdict.action is ArmorAction.BLOCK or verdict.sanitized_text is None:
                raise GatewayDeniedError(GatewayReason.OUTPUT_BLOCKED, GatewayStage.OUTPUT_ARMOR)
        if verdict.action is ArmorAction.REDACT:
            return GatewayResult(
                decision=GatewayDecision.REDACT,
                reason=GatewayReason.OUTPUT_PII_REDACTED,
                output=verdict.sanitized_text,
            )
        if screened.redacted:
            return GatewayResult(
                decision=GatewayDecision.REDACT,
                reason=GatewayReason.INPUT_PII_REDACTED,
                output=verdict.sanitized_text,
            )
        return GatewayResult(
            decision=GatewayDecision.ALLOW, reason=GatewayReason.OK, output=verdict.sanitized_text
        )

    async def _invoke(self, tool: RegisteredTool, arguments: dict[str, Any]) -> str:
        failure: Exception | None = None
        output = ""
        with self._parts.tracer.span("tool", {attributes.TOOL: tool.spec.name}):
            try:
                output = await tool.handler(arguments)
            except Exception as error:
                failure = error
        if failure is not None:
            raise ToolExecutionError(failure)
        return output

    def _finish(
        self,
        root: SafeSpan,
        principal: AgentPrincipal | None,
        tool_name: str,
        outcome: GatewayOutcome,
    ) -> None:
        root.set_all({attributes.DECISION: outcome.decision.value, "reason": outcome.reason.value})
        with self._parts.tracer.span("audit", {attributes.DECISION: outcome.decision.value}):
            self._parts.auditor.record(principal, tool_name, outcome)
