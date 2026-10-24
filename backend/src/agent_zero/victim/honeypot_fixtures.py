import zlib
from typing import NamedTuple

from agent_zero.victim.schemas import Order


class DecoyOrder(NamedTuple):
    merchant: str
    pickup_address: str
    delivery_address: str
    items: tuple[str, ...]


# Lo que ve en el señuelo quien ya fue desviado: comercio, artículos y direcciones coherentes
# entre sí (la misma ciudad) pero fabricados, para no exponer los del entorno protegido. Las
# direcciones usan el mismo estilo ficticio que las reales, para no delatar el señuelo.
HONEYPOT_ORDERS: tuple[DecoyOrder, ...] = (
    DecoyOrder(
        "Smash Burger Co. · Chacao",
        "Av. Simulada 7, C.C. Ensayo, local 12, Chacao, Caracas",
        "Calle Ficticia 31, Edif. Réplica, piso 2, El Rosal, Caracas",
        ("Hamburguesa clásica x2", "Papas fritas", "Refresco 355 ml"),
    ),
    DecoyOrder(
        "Napoli Express · La Viña",
        "Av. Prueba 52, local 4, La Viña, Valencia",
        "Calle Ensayo 19, Res. Réplica, apto 3-1, Los Mangos, Valencia",
        ("Pizza margarita mediana", "Pan de ajo"),
    ),
    DecoyOrder(
        "Pollos La Granja · Naguanagua",
        "Av. Laboratorio 210, local 1, Naguanagua, Carabobo",
        "Calle Simulada 6, Qta. Réplica, Naguanagua, Carabobo",
        ("Medio pollo a la brasa", "Yuca frita", "Refresco 1,5 L"),
    ),
    DecoyOrder(
        "Excelsior Gama · Los Dos Caminos",
        "Av. Ficticia 3, C.C. Prueba, Los Dos Caminos, Caracas",
        "Calle Demo 44, Edif. Réplica, piso 9, Sebucán, Caracas",
        ("Arroz Mary 1 kg x2", "Pasta Primor 1 kg", "Azúcar"),
    ),
    DecoyOrder(
        "Locatel · La Lago",
        "Av. Ensayo 18, local 7, La Lago, Maracaibo",
        "Calle Prueba 27, Edif. Réplica, piso 5, La Lago, Maracaibo",
        ("Ibuprofeno 400 mg (10 tab)", "Tapabocas (50 und)"),
    ),
    DecoyOrder(
        "Wasabi Lounge · San Diego",
        "Av. Sintética 95, local 2, San Diego, Carabobo",
        "Calle Laboratorio 12, Res. Réplica, torre A, San Diego, Carabobo",
        ("Roll California (10 pzs)", "Edamame"),
    ),
)


def _differs(decoy: DecoyOrder, order: Order) -> bool:
    return (
        decoy.merchant != order.merchant
        and decoy.pickup_address != order.pickup_address
        and decoy.delivery_address != order.delivery_address
    )


def honeypot_order(order: Order) -> Order:
    """Devuelve el pedido señuelo estable para `order`, sin ningún dato del comercio real."""
    start = zlib.crc32(order.order_id.encode()) % len(HONEYPOT_ORDERS)
    for offset in range(len(HONEYPOT_ORDERS)):
        decoy = HONEYPOT_ORDERS[(start + offset) % len(HONEYPOT_ORDERS)]
        if _differs(decoy, order):
            return order.model_copy(update=decoy._asdict())
    raise ValueError("No hay un pedido señuelo distinto del real.")
