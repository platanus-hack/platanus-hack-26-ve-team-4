from agent_zero.victim.fixtures import (
    HONEYPOT_ORDERS,
    ORDERS,
    customer_ids,
    honeypot_order,
    orders_for_customer,
)
from agent_zero.victim.schemas import Order


def _all_orders() -> list[Order]:
    return [order for customer in customer_ids(500) for order in orders_for_customer(customer)]


def test_every_order_has_a_decoy_from_another_merchant_with_other_items() -> None:
    for order in _all_orders():
        merchant, items = honeypot_order(order)

        assert merchant != order.merchant, order.order_id
        assert set(items).isdisjoint(order.items), order.order_id


def test_the_decoy_is_stable_and_varies_between_orders() -> None:
    seeded = list(ORDERS.values())

    assert [honeypot_order(order) for order in seeded] == [honeypot_order(o) for o in seeded]
    assert len({honeypot_order(order)[0] for order in _all_orders()}) == len(HONEYPOT_ORDERS)
