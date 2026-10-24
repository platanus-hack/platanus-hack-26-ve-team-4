import json

import pytest

from agent_zero.agent_gateway.tool_registry import ToolRegistry
from agent_zero.victim.store_tools import (
    UnknownOrderError,
    get_order,
    register_store_tools,
    request_refund,
    search_knowledge,
)


async def test_get_order_only_returns_the_customers_own_order() -> None:
    order = json.loads(await get_order({"customer_id": "cust-ana", "order_id": "A-1001"}))

    assert order["status"] == "en camino"
    with pytest.raises(UnknownOrderError):
        await get_order({"customer_id": "cust-bruno", "order_id": "A-1001"})


async def test_knowledge_search_matches_keywords() -> None:
    result = json.loads(await search_knowledge({"query": "¿Dónde viene mi pedido?"}))

    assert any("días hábiles" in answer for answer in result["articles"])


async def test_refund_respects_the_limit() -> None:
    small = json.loads(
        await request_refund({"customer_id": "cust-ana", "order_id": "A-1001", "amount": 20})
    )
    large = json.loads(
        await request_refund({"customer_id": "cust-ana", "order_id": "A-1001", "amount": 21})
    )

    assert small["approved"] is True
    assert large["approved"] is False


def test_all_store_tools_are_registered() -> None:
    registry = ToolRegistry()

    register_store_tools(registry)

    assert registry.names() == ("get_order", "request_refund", "search_knowledge")
