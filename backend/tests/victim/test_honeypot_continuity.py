"""Continuidad del señuelo: al desviar, los pedidos propios no cambian y los ajenos son falsos."""

import json
from typing import Any, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent_zero.agent_gateway.business_policy import CallContext
from agent_zero.arena.core import ProductCore
from agent_zero.shared.database import Database
from agent_zero.victim.arena_manifest import ARENA_VERSION
from agent_zero.victim.environments import Environment
from agent_zero.victim.fixtures import ORDERS, orders_for_customer
from agent_zero.victim.honeypot_fixtures import FABRICATED_FIELDS, honeypot_order
from agent_zero.victim.honeypot_view import session_order

pytestmark = pytest.mark.requirement("CORE-06")

OWNER = "cust-demo-0032"
VISIBLE_FIELDS = (
    "order_id",
    "customer_name",
    "customer_email",
    "merchant",
    "pickup_address",
    "delivery_address",
    "status",
    "items",
    "total",
    "refunded",
)


def _core(client: TestClient) -> ProductCore:
    return cast(ProductCore, cast(FastAPI, client.app).state.core)


def _context(environment: str, customer: str, operation_id: str) -> CallContext:
    return CallContext(
        attempt_id=f"attempt-{operation_id}",
        session_id=f"internal-continuity-{customer}",
        session_customer_id=customer,
        environment=environment,
        policy_version=0,
        run_id=f"run-{operation_id}",
        operation_id=operation_id,
    )


async def _read(core: ProductCore, context: CallContext, order_id: str) -> dict[str, Any]:
    await core.ensure_agents()
    for customer in (context.session_customer_id, OWNER):
        await core.environments.ensure_customer(customer)
    principal = await core.fleet.admission.admit("soporte-tienda", ARENA_VERSION)
    output = await core.scenario.call("get_order", {"order_id": order_id}, context, principal)
    return cast(dict[str, Any], json.loads(output.text))


def _get(client: TestClient, environment: str, customer: str, order_id: str) -> dict[str, Any]:
    assert client.portal is not None
    context = _context(environment, customer, f"{environment}-{customer}-{order_id}")
    return client.portal.call(_read, _core(client), context, order_id)


def _visible(order: dict[str, Any]) -> dict[str, Any]:
    return {field: order[field] for field in VISIBLE_FIELDS}


def test_the_own_order_looks_the_same_before_and_after_the_diversion(client: TestClient) -> None:
    for order in orders_for_customer(OWNER):
        protected = _get(client, "protected", OWNER, order.order_id)
        honeypot = _get(client, "honeypot", OWNER, order.order_id)

        assert _visible(honeypot) == _visible(protected), order.order_id
        assert honeypot["customer_name"] == "Rafael Rodríguez"
        assert protected["canary"].startswith("AZP_")
        assert honeypot["canary"].startswith("AZH_")
        assert protected["canary"] not in json.dumps(honeypot, ensure_ascii=False)


def test_an_order_of_another_customer_is_fabricated_in_the_honeypot(client: TestClient) -> None:
    real = ORDERS["B-2001"]
    decoy = honeypot_order(real).model_dump(mode="json")

    shown = _get(client, "honeypot", "cust-ana", "B-2001")

    assert shown["canary"].startswith("AZH_")
    for field in FABRICATED_FIELDS:
        assert shown[field] == decoy[field], field
        assert shown[field] != real.model_dump(mode="json")[field], field


def test_two_orders_of_another_customer_share_one_fake_identity_and_destination(
    client: TestClient,
) -> None:
    real = orders_for_customer(OWNER)
    shown = [_get(client, "honeypot", "cust-ana", order.order_id) for order in real]

    assert len({(o["customer_name"], o["customer_email"]) for o in shown}) == 1
    assert len({o["delivery_address"] for o in shown}) == 1
    assert shown[0]["customer_name"] != real[0].customer_name
    assert shown[0]["delivery_address"] != real[0].delivery_address


async def test_the_own_view_needs_no_protected_database() -> None:
    # Solo existe la base del señuelo: los datos propios salen de los fixtures en código.
    environment = Environment(Database("sqlite+aiosqlite://"), "honeypot", "test-honeypot")
    try:
        await environment.initialize()
        stored = await environment.order("A-1001")
    finally:
        await environment.database.dispose()
    assert stored is not None
    real = ORDERS["A-1001"].model_dump(mode="json")

    own = session_order("honeypot", stored, "cust-ana")
    other = session_order("honeypot", stored, "cust-bruno")

    assert stored["merchant"] != real["merchant"]
    assert {field: own[field] for field in FABRICATED_FIELDS} == {
        field: real[field] for field in FABRICATED_FIELDS
    }
    assert own["canary"] == stored["canary"]
    assert own["canary"].startswith("AZH_")
    assert other == stored
    assert session_order("protected", stored, "cust-ana") == stored
