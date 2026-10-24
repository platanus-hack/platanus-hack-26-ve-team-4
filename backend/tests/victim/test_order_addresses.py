import json
from typing import Any

from agent_zero.shared.database import Database
from agent_zero.victim.environments import Environment
from agent_zero.victim.fixtures import (
    ORDERS,
    SYNTHETIC_CUSTOMER_IDS,
    customer_ids,
    demo_delivery_address,
    orders_for_customer,
)
from agent_zero.victim.store_tools import get_order
from agent_zero.victim.tool_schemas import ARGUMENT_MODELS

ADDRESS_FIELDS = ("pickup_address", "delivery_address")


def _city(address: str) -> str:
    return address.rsplit(", ", 1)[1]


def test_each_customer_has_one_destination_in_the_city_of_its_merchants() -> None:
    pickups: dict[str, set[str]] = {}
    for customer in customer_ids(500):
        orders = orders_for_customer(customer)

        assert len({order.delivery_address for order in orders}) == 1, customer
        for order in orders:
            assert _city(order.pickup_address) == _city(order.delivery_address), order.order_id
            pickups.setdefault(order.merchant, set()).add(order.pickup_address)
    assert all(len(addresses) == 1 for addresses in pickups.values()), pickups
    seeded = {orders_for_customer(c)[0].delivery_address for c in SYNTHETIC_CUSTOMER_IDS}
    assert len(seeded) == len(SYNTHETIC_CUSTOMER_IDS)


def test_demo_destination_is_deterministic_and_derived_from_the_number() -> None:
    first = orders_for_customer("cust-demo-0042")

    assert first == orders_for_customer("cust-demo-0042")
    assert first[0].delivery_address == demo_delivery_address(42)
    assert "Calle Demo 42," in first[0].delivery_address
    assert demo_delivery_address(42) != demo_delivery_address(43)


async def test_get_order_returns_both_addresses_of_the_own_order() -> None:
    expected = ORDERS["A-1001"]

    order = json.loads(await get_order({"customer_id": "cust-ana", "order_id": "A-1001"}))

    assert order["pickup_address"] == expected.pickup_address
    assert order["delivery_address"] == expected.delivery_address


async def test_seeded_environments_expose_real_addresses_only_in_protected() -> None:
    expected = ORDERS["B-2001"]
    found: dict[str, dict[str, Any] | None] = {}
    for name in ("protected", "honeypot"):
        environment = Environment(Database("sqlite+aiosqlite://"), name, f"test-{name}")
        try:
            await environment.initialize()
            found[name] = await environment.order("B-2001")
        finally:
            await environment.database.dispose()

    protected, honeypot = found["protected"], found["honeypot"]
    assert protected is not None
    assert honeypot is not None
    assert [protected[field] for field in ADDRESS_FIELDS] == [
        expected.pickup_address,
        expected.delivery_address,
    ]
    assert honeypot["delivery_address"] != expected.delivery_address
    assert honeypot["pickup_address"] != expected.pickup_address


def test_no_tool_argument_can_change_an_address() -> None:
    for model in ARGUMENT_MODELS.values():
        assert not set(model.model_fields) & {*ADDRESS_FIELDS, "address", "direccion"}
