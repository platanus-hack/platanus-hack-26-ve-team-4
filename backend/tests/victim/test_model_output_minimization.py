import json
from typing import Any, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent_zero.agent_gateway.business_policy import CallContext
from agent_zero.arena.core import ProductCore
from agent_zero.victim.arena_manifest import ARENA_VERSION
from agent_zero.victim.fixtures import orders_for_customer

pytestmark = pytest.mark.requirement("CORE-06")

OWNER = "cust-demo-0032"
ENVIRONMENTS = ("protected", "honeypot")
ORDER_ID = orders_for_customer(OWNER)[0].order_id


def _core(client: TestClient) -> ProductCore:
    return cast(ProductCore, cast(FastAPI, client.app).state.core)


def _context(environment: str, customer: str, operation_id: str) -> CallContext:
    return CallContext(
        attempt_id=f"attempt-{operation_id}",
        session_id=f"internal-minimization-{operation_id}",
        session_customer_id=customer,
        environment=environment,
        policy_version=0,
        run_id=f"run-{operation_id}",
        operation_id=operation_id,
    )


async def _call(
    core: ProductCore, context: CallContext, tool: str, arguments: dict[str, Any]
) -> tuple[str, dict[str, Any]]:
    await core.ensure_agents()
    await core.environments.ensure_customer(context.session_customer_id)
    principal = await core.fleet.admission.admit("soporte-tienda", ARENA_VERSION)
    output = await core.scenario.call(tool, arguments, context, principal)
    return output.text, cast(dict[str, Any], output.effect)


def _run(
    client: TestClient, environment: str, customer: str, tool: str, arguments: dict[str, Any]
) -> tuple[str, dict[str, Any]]:
    assert client.portal is not None
    context = _context(environment, customer, f"{tool[:3]}-{environment[:2]}-{customer[-4:]}")
    return cast(
        tuple[str, dict[str, Any]],
        client.portal.call(_call, _core(client), context, tool, arguments),
    )


@pytest.mark.parametrize("environment", ENVIRONMENTS)
def test_get_order_hides_internal_customer_identifiers(
    client: TestClient, environment: str
) -> None:
    text, effect = _run(client, environment, OWNER, "get_order", {"order_id": ORDER_ID})

    assert "customer_id" not in json.loads(text)
    assert "cust-" not in text
    assert effect["owner_customer_id"] == OWNER


@pytest.mark.parametrize("environment", ENVIRONMENTS)
def test_request_refund_hides_internal_customer_identifiers(
    client: TestClient, environment: str
) -> None:
    arguments = {"order_id": ORDER_ID, "amount": 5}

    text, effect = _run(client, environment, OWNER, "request_refund", arguments)

    assert "customer_id" not in json.loads(text)
    assert "cust-" not in text
    assert effect["owner_customer_id"] == OWNER


@pytest.mark.parametrize(
    ("tool", "arguments"),
    [
        ("get_order", {"order_id": ORDER_ID}),
        ("request_refund", {"order_id": ORDER_ID, "amount": 5}),
    ],
)
@pytest.mark.parametrize("customer", [OWNER, "cust-ana"])
def test_protected_and_honeypot_expose_the_same_keys(
    client: TestClient, tool: str, arguments: dict[str, Any], customer: str
) -> None:
    keys = {
        environment: set(json.loads(_run(client, environment, customer, tool, arguments)[0]))
        for environment in ENVIRONMENTS
    }

    assert keys["protected"] == keys["honeypot"]
