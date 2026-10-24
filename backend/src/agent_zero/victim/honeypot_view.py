from typing import Any

from agent_zero.victim.fixtures import orders_for_customer
from agent_zero.victim.honeypot_fixtures import FABRICATED_FIELDS
from agent_zero.victim.schemas import Order

DECOY_ENVIRONMENT = "honeypot"


def _fixture_order(customer_id: str, order_id: str) -> Order | None:
    try:
        orders = orders_for_customer(customer_id)
    except ValueError:
        return None
    return next((order for order in orders if order.order_id == order_id), None)


def session_order(
    environment_name: str, data: dict[str, Any], session_customer_id: str
) -> dict[str, Any]:
    """El pedido guardado tal como lo ve la sesión que lo consulta.

    En el señuelo, un pedido del cliente de la sesión recupera los campos fabricados desde los
    fixtures en código, así que se ve igual que en el protegido y el desvío no cambia los datos
    propios. Nunca se lee la base protegida. El resto del registro (canario `AZH_`, estado,
    total) sigue siendo el del señuelo, y los pedidos ajenos quedan fabricados.
    """
    if environment_name != DECOY_ENVIRONMENT or data.get("customer_id") != session_customer_id:
        return dict(data)
    own = _fixture_order(session_customer_id, str(data.get("order_id", "")))
    if own is None:
        return dict(data)
    return dict(data) | own.model_dump(mode="json", include=set(FABRICATED_FIELDS))
