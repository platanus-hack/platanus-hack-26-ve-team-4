import json
from typing import Any

from agent_zero.victim.fixtures import customer_name_of, orders_for_customer
from agent_zero.victim.holder_context import holder_context


class Store:
    def __init__(self, rows: dict[str, dict[str, Any]]) -> None:
        self._rows = rows

    async def order(self, order_id: str) -> dict[str, Any] | None:
        return self._rows.get(order_id)


def _rows(customer_id: str) -> dict[str, dict[str, Any]]:
    return {
        order.order_id: order.model_dump(mode="json") | {"refunded": 0.0}
        for order in orders_for_customer(customer_id)
    }


async def test_the_holder_gets_their_name_and_orders_without_personal_data() -> None:
    holder = await holder_context(Store(_rows("cust-demo-0074")), "cust-demo-0074")

    assert holder["nombre"] == customer_name_of("cust-demo-0074")
    assert [order["pedido"] for order in holder["pedidos"]] == ["D-74001", "D-74002"]
    assert [order["estado"] for order in holder["pedidos"]] == ["en camino", "entregado"]
    text = json.dumps(holder, ensure_ascii=False)
    seeded = orders_for_customer("cust-demo-0074")[0]
    for private in (seeded.customer_email, seeded.delivery_address, "cust-demo-0074"):
        assert private not in text


async def test_the_holder_sees_the_current_state_of_the_store() -> None:
    rows = _rows("cust-demo-0074")
    rows["D-74001"] |= {"status": "entregado", "refunded": 12.5}

    holder = await holder_context(Store(rows), "cust-demo-0074")

    assert holder["pedidos"][0] | {"articulos": []} == {
        "pedido": "D-74001",
        "comercio": rows["D-74001"]["merchant"],
        "estado": "entregado",
        "articulos": [],
        "total_usd": 45,
        "reembolsado_usd": 12.5,
    }


async def test_a_missing_row_falls_back_to_the_seeded_order() -> None:
    holder = await holder_context(Store({}), "cust-demo-0074")

    assert [order["reembolsado_usd"] for order in holder["pedidos"]] == [0, 0]
