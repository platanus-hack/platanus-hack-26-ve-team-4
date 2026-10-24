import json
from typing import Any

from agent_zero.agent_gateway.schemas import ToolSpec
from agent_zero.agent_gateway.tool_registry import ToolRegistry
from agent_zero.shared.classification import DataClassification
from agent_zero.victim.fixtures import ORDERS, REFUND_LIMIT
from agent_zero.victim.knowledge import KNOWLEDGE
from agent_zero.victim.models import ToolName

STORE_REGION = "ve"

TOOL_SPECS: dict[ToolName, ToolSpec] = {
    ToolName.GET_ORDER: ToolSpec(
        name=ToolName.GET_ORDER.value,
        classification=DataClassification.INTERNAL,
        region=STORE_REGION,
        required_scope="tool:get_order",
    ),
    ToolName.SEARCH_KNOWLEDGE: ToolSpec(
        name=ToolName.SEARCH_KNOWLEDGE.value,
        classification=DataClassification.PUBLIC,
        region=STORE_REGION,
        required_scope="tool:search_knowledge",
    ),
    ToolName.REQUEST_REFUND: ToolSpec(
        name=ToolName.REQUEST_REFUND.value,
        classification=DataClassification.CONFIDENTIAL,
        region=STORE_REGION,
        required_scope="tool:request_refund",
    ),
}


class UnknownOrderError(LookupError):
    pass


def _owned_order(arguments: dict[str, Any]) -> dict[str, Any]:
    order = ORDERS.get(str(arguments.get("order_id", "")))
    if order is None or order.customer_id != arguments.get("customer_id"):
        raise UnknownOrderError("pedido inexistente para este cliente")
    return order.model_dump(mode="json")


async def get_order(arguments: dict[str, Any]) -> str:
    return json.dumps(_owned_order(arguments), ensure_ascii=False)


async def search_knowledge(arguments: dict[str, Any]) -> str:
    query = str(arguments.get("query", "")).casefold()
    hits = [
        article.answer
        for article in KNOWLEDGE
        if any(keyword in query for keyword in article.keywords)
    ]
    return json.dumps({"articles": hits}, ensure_ascii=False)


async def request_refund(arguments: dict[str, Any]) -> str:
    order = _owned_order(arguments)
    amount = int(arguments.get("amount", 0))
    approved = 0 < amount <= min(REFUND_LIMIT, order["total"])
    return json.dumps({"order_id": order["order_id"], "approved": approved, "amount": amount})


def register_store_tools(registry: ToolRegistry) -> None:
    registry.register(TOOL_SPECS[ToolName.GET_ORDER], get_order)
    registry.register(TOOL_SPECS[ToolName.SEARCH_KNOWLEDGE], search_knowledge)
    registry.register(TOOL_SPECS[ToolName.REQUEST_REFUND], request_refund)
