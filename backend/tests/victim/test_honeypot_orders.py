import pytest

from agent_zero.victim.customer_names import customer_email, demo_number
from agent_zero.victim.fixtures import ORDERS, customer_ids, orders_for_customer
from agent_zero.victim.honeypot_fixtures import HONEYPOT_ORDERS, honeypot_order
from agent_zero.victim.schemas import Order


def _all_orders() -> list[Order]:
    return [order for customer in customer_ids(500) for order in orders_for_customer(customer)]


def test_every_order_has_a_decoy_from_another_merchant_with_other_items() -> None:
    for order in _all_orders():
        decoy = honeypot_order(order)

        assert decoy.merchant != order.merchant, order.order_id
        assert set(decoy.items).isdisjoint(order.items), order.order_id


@pytest.mark.requirement("CORE-06")
def test_the_decoy_never_reveals_the_real_pickup_or_delivery_address() -> None:
    real = {order.pickup_address for order in _all_orders()}
    real |= {order.delivery_address for order in _all_orders()}

    for order in _all_orders():
        decoy = honeypot_order(order)

        assert decoy.delivery_address != order.delivery_address, order.order_id
        assert decoy.pickup_address != order.pickup_address, order.order_id
        assert {decoy.pickup_address, decoy.delivery_address}.isdisjoint(real), order.order_id
        assert decoy.model_dump(include={"order_id", "customer_id", "status", "total"}) == (
            order.model_dump(include={"order_id", "customer_id", "status", "total"})
        )


def test_the_decoy_is_stable_and_varies_between_orders() -> None:
    seeded = list(ORDERS.values())

    assert [honeypot_order(order) for order in seeded] == [honeypot_order(o) for o in seeded]
    assert len({honeypot_order(order).merchant for order in _all_orders()}) == len(HONEYPOT_ORDERS)


def test_decoy_addresses_are_in_the_city_of_their_merchant() -> None:
    for decoy in HONEYPOT_ORDERS:
        city = decoy.pickup_address.rsplit(", ", 1)[1]

        assert decoy.delivery_address.endswith(f", {city}"), decoy.merchant


@pytest.mark.requirement("CORE-06")
def test_the_decoy_never_reveals_a_real_customer_name_or_email() -> None:
    real_names = {order.customer_name for order in _all_orders()}
    real_emails = {order.customer_email for order in _all_orders()}

    for order in _all_orders():
        decoy = honeypot_order(order)

        assert decoy.customer_name not in real_names, order.order_id
        assert decoy.customer_email not in real_emails, order.order_id


def test_the_decoy_identity_is_the_same_in_every_order_of_a_customer() -> None:
    for customer in customer_ids(500):
        decoys = [honeypot_order(order) for order in orders_for_customer(customer)]

        assert len({(d.customer_name, d.customer_email) for d in decoys}) == 1, customer
        name = decoys[0].customer_name
        assert decoys[0].customer_email == customer_email(name, demo_number(customer)), customer
