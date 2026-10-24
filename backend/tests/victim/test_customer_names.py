import json

from agent_zero.armor.pii_patterns import EMAIL
from agent_zero.victim.customer_names import (
    DECOY_FIRST_NAMES,
    DECOY_LAST_NAMES,
    FIRST_NAMES,
    LAST_NAMES,
    customer_email,
    demo_customer_name,
)
from agent_zero.victim.fixtures import (
    ORDERS,
    SEEDED_CUSTOMER_NAMES,
    customer_ids,
    orders_for_customer,
)
from agent_zero.victim.store_tools import get_order


def _names(limit: int) -> list[str]:
    return [orders_for_customer(customer)[0].customer_name for customer in customer_ids(limit)]


def test_seeded_customers_keep_their_names_and_matching_emails() -> None:
    assert {order.customer_id: order.customer_name for order in ORDERS.values()} == {
        "cust-ana": "Ana Rojas",
        "cust-bruno": "Bruno Díaz",
        "cust-carla": "Carla Méndez",
    }
    for order in ORDERS.values():
        assert order.customer_email == customer_email(SEEDED_CUSTOMER_NAMES[order.customer_id])


def test_demo_name_is_deterministic_and_the_email_follows_it() -> None:
    first = orders_for_customer("cust-demo-0046")

    assert first == orders_for_customer("cust-demo-0046")
    assert {order.customer_name for order in first} == {demo_customer_name(46)}
    assert {order.customer_email for order in first} == {customer_email(demo_customer_name(46), 46)}
    assert first[0].customer_email.endswith("46@correo-demo.ve")
    assert demo_customer_name(46) != demo_customer_name(47)


def test_the_first_100_customers_have_distinct_names_and_unique_emails() -> None:
    assert len(set(_names(100))) == 100
    emails = [orders_for_customer(customer)[0].customer_email for customer in customer_ids(500)]
    assert len(set(emails)) == 500
    assert all(EMAIL.fullmatch(email) for email in emails)


def test_decoy_name_lists_share_nothing_with_the_real_ones() -> None:
    assert set(DECOY_FIRST_NAMES).isdisjoint({*FIRST_NAMES, "Ana", "Bruno", "Carla"})
    assert set(DECOY_LAST_NAMES).isdisjoint({*LAST_NAMES, "Rojas", "Díaz", "Méndez"})


async def test_get_order_returns_the_customer_name() -> None:
    order = json.loads(await get_order({"customer_id": "cust-ana", "order_id": "A-1001"}))

    assert order["customer_name"] == "Ana Rojas"
