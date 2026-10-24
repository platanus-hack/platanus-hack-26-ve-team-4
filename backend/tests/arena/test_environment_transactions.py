import asyncio
import json
from dataclasses import replace
from typing import cast

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from agent_zero.agent_gateway.business_policy import CallContext, using_call_context
from agent_zero.agent_gateway.errors import GatewayDeniedError
from agent_zero.arena.core import ProductCore
from agent_zero.fleet.fleet_builder import build_fleet
from agent_zero.policies.policy_engine import BusinessPolicyEngine
from agent_zero.victim.arena_manifest import ARENA_VERSION
from agent_zero.victim.environments import Environments
from agent_zero.victim.scenario_tools import ScenarioTools
from agent_zero.victim.store_models import StoreRefund
from agent_zero.victim.store_tools import register_store_tools
from tests.arena.support import join


def test_independent_workers_serialize_authorization_with_the_effect(
    manual_client: TestClient,
) -> None:
    join(manual_client)
    core: ProductCore = cast(FastAPI, manual_client.app).state.core

    async def race() -> None:
        # Independent pools and locks model separate processes sharing the same databases.
        other = Environments(core.fleet.settings)
        await other.initialize()
        fleet = build_fleet(core.fleet.settings, core.fleet.database)
        register_store_tools(fleet.tools)
        ScenarioTools(fleet, other).register()
        fleet.gateway.configure_business_layer(
            BusinessPolicyEngine(fleet.database, other),
            core.observer,
            lambda context: other.for_context(context).transaction(),
        )
        version = await core.policies.propose("race-test", "OBJ-REFUND")
        assert version is not None
        principals = [
            await selected.admission.admit("soporte-tienda", ARENA_VERSION)
            for selected in (core.fleet, fleet)
        ]
        context = CallContext(
            attempt_id="refund-race",
            session_id="race",
            session_customer_id="cust-ana",
            environment="protected",
            policy_version=version,
            run_id="run-race",
        )

        async def refund(index: int, operation: str) -> str:
            selected = (core.fleet, fleet)[index]
            with using_call_context(replace(context, operation_id=operation)):
                try:
                    return await selected.tools_for(principals[index]).call_tool(
                        "request_refund", {"order_id": "A-1001", "amount": 15}
                    )
                except GatewayDeniedError:
                    return "denied"

        try:
            outcomes = await asyncio.gather(refund(0, "first"), refund(1, "second"))
            assert outcomes.count("denied") == 1, outcomes
            order = await other.get("protected").order("A-1001")
            assert order is not None
            assert order["refunded"] == 15
            successful_operation = "first" if outcomes[0] != "denied" else "second"
            repeated = await asyncio.gather(
                refund(0, successful_operation), refund(1, successful_operation)
            )
            assert repeated[0] == repeated[1]
            assert json.loads(repeated[0])["refunded_total"] == 15
            async with other.get("protected").database.sessions() as db:
                assert await db.scalar(select(func.count()).select_from(StoreRefund)) == 1
            assert await other.get("honeypot").order("A-1001") != order
        finally:
            await other.dispose()

    assert manual_client.portal is not None
    manual_client.portal.call(race)
