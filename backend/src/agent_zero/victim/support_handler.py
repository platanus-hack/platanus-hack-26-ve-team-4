import json
from datetime import timedelta
from typing import Any

from agent_zero.agent_gateway.errors import GatewayDeniedError
from agent_zero.fleet.fleet_builder import Fleet
from agent_zero.llm.errors import ModelRefusedError
from agent_zero.memory_bank.memory_read_service import MemoryReadService
from agent_zero.memory_bank.memory_write_service import MemoryWriteService
from agent_zero.memory_bank.models import MemoryKind
from agent_zero.memory_bank.schemas import MemoryWriteRequest
from agent_zero.runtime.handlers import StepContext
from agent_zero.runtime.step_results import Complete, StepResult, Wait
from agent_zero.runtime.tool_access import ToolAccess
from agent_zero.victim.manifest import SUPPORT_HANDLER
from agent_zero.victim.reply_composer import ReplyComposer
from agent_zero.victim.schemas import SupportRequest

FOLLOW_UP_STAGE = "follow_up"


class SupportConversationHandler:
    name = SUPPORT_HANDLER

    def __init__(self, fleet: Fleet, composer: ReplyComposer) -> None:
        self._fleet = fleet
        self._composer = composer

    async def step(self, context: StepContext) -> StepResult:
        if context.checkpoint.get("stage") == FOLLOW_UP_STAGE:
            output = dict(context.checkpoint["output"])
            output["followed_up_at"] = context.now.isoformat()
            return Complete(output=output)
        return await self._answer(context, SupportRequest.model_validate(context.input))

    async def _answer(self, context: StepContext, request: SupportRequest) -> StepResult:
        if context.tools is None:
            return Complete(output={"outcome": "sin_acceso_a_herramientas"})
        memories = await self._recall(context, request.customer_id)
        try:
            knowledge = await context.tools.call_tool(
                "search_knowledge", {"query": request.message}
            )
        except GatewayDeniedError as denial:
            return Complete(output={"outcome": "bloqueado", "reason": denial.reason.value})
        order = json.loads(
            await context.tools.call_tool(
                "get_order", {"customer_id": request.customer_id, "order_id": request.order_id}
            )
        )
        output: dict[str, Any] = {
            "outcome": "respondido",
            "order_status": order.get("status"),
            "order_seen_by_agent": order,
            "memories_recalled": len(memories),
            "refund": await self._refund(context.tools, request),
        }
        try:
            output["reply"] = await self._composer.compose(
                request.message, order, json.loads(knowledge)["articles"], memories
            )
        except ModelRefusedError:
            output["outcome"] = "rechazado_por_el_modelo"
        await self._remember(context, request, str(output.get("order_status")))
        if request.follow_up_seconds is None:
            return Complete(output=output)
        return Wait(
            until=context.now + timedelta(seconds=request.follow_up_seconds),
            checkpoint={"stage": FOLLOW_UP_STAGE, "output": output},
        )

    async def _refund(self, tools: ToolAccess, request: SupportRequest) -> dict[str, Any] | None:
        if request.refund_amount is None:
            return None
        arguments = {
            "customer_id": request.customer_id,
            "order_id": request.order_id,
            "amount": request.refund_amount,
        }
        try:
            return {"result": json.loads(await tools.call_tool("request_refund", arguments))}
        except GatewayDeniedError as denial:
            return {"denied": denial.reason.value, "stage": denial.stage.value}

    async def _recall(self, context: StepContext, subject_id: str) -> list[str]:
        async with self._fleet.database.sessions() as db:
            reader = MemoryReadService(
                db, self._fleet.cipher, self._fleet.memory_guard, self._fleet.clock
            )
            return [item.content for item in await reader.recall(context.principal, subject_id)]

    async def _remember(self, context: StepContext, request: SupportRequest, status: str) -> None:
        note = MemoryWriteRequest(
            subject_id=request.customer_id,
            kind=MemoryKind.EVENT,
            content=f"Consultó el pedido {request.order_id} ({status}): {request.message}",
            source_run_id=context.run_id,
        )
        async with self._fleet.database.sessions() as db:
            writer = MemoryWriteService(
                db,
                self._fleet.settings,
                self._fleet.cipher,
                self._fleet.memory_guard,
                self._fleet.clock,
            )
            await writer.write(context.principal, note)
