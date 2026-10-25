from typing import Any, Protocol

from agent_zero.victim.fixtures import customer_name_of, orders_for_customer


class OrderReader(Protocol):
    async def order(self, order_id: str) -> dict[str, Any] | None: ...


async def holder_context(environment: OrderReader, customer_id: str) -> dict[str, Any]:
    """Lo que el asistente sabe del titular verificado: su nombre y sus pedidos al día.

    Sin correo, direcciones ni el id interno: el modelo no los necesita para atenderlo.
    """
    orders = []
    for seeded in orders_for_customer(customer_id):
        current = await environment.order(seeded.order_id) or seeded.model_dump()
        orders.append(
            {
                "pedido": current["order_id"],
                "comercio": current["merchant"],
                "estado": current["status"],
                "articulos": list(current["items"]),
                "total_usd": current["total"],
                "reembolsado_usd": current.get("refunded", 0),
            }
        )
    return {"nombre": customer_name_of(customer_id), "pedidos": orders}
