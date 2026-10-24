import json
from typing import cast

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from agent_zero.agent_gateway.business_policy import CallContext, using_call_context
from agent_zero.arena.core import ProductCore
from agent_zero.events.models import EventType
from agent_zero.events.schemas import EventDraft
from agent_zero.victim.arena_manifest import ARENA_VERSION
from agent_zero.victim.store_models import StoreRefund
from tests.arena.support import join


def test_completed_tool_operation_is_not_repeated_on_retry(manual_client: TestClient) -> None:
    join(manual_client)
    core: ProductCore = cast(FastAPI, manual_client.app).state.core

    async def repeated_refund() -> int:
        principal = await core.fleet.admission.admit("soporte-tienda", ARENA_VERSION)
        tools = core.fleet.tools_for(principal)
        context = CallContext(
            attempt_id="attempt-retry",
            session_id="internal-retry",
            session_customer_id="cust-ana",
            environment="protected",
            policy_version=0,
            run_id="run-retry",
            operation_id="refund-retry",
        )
        with using_call_context(context):
            first = await tools.call_tool("request_refund", {"order_id": "A-1001", "amount": 10})
            second = await tools.call_tool("request_refund", {"order_id": "A-1001", "amount": 10})
        assert first == second
        assert json.loads(first)["refunded_total"] == 10
        async with core.environments.get("protected").database.sessions() as db:
            return int(await db.scalar(select(func.count()).select_from(StoreRefund)) or 0)

    assert manual_client.portal is not None
    assert manual_client.portal.call(repeated_refund) == 1


def test_redacting_numeric_pii_does_not_corrupt_event_json(manual_client: TestClient) -> None:
    core: ProductCore = cast(FastAPI, manual_client.app).state.core

    async def record() -> str:
        event = await core.events.emit(
            EventDraft(
                type=EventType.TOOL_PROPOSED,
                data={"number": 4111111111111111, "amount": 12.5, "nested": ["a@example.com"]},
            )
        )
        assert event.data["amount"] == 12.5
        return event.model_dump_json()

    assert manual_client.portal is not None
    result = manual_client.portal.call(record)
    assert "4111111111111111" not in result
    assert "a@example.com" not in result
