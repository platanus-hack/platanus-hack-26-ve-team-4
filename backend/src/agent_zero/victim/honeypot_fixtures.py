import zlib
from typing import NamedTuple

from agent_zero.victim.customer_names import decoy_identity
from agent_zero.victim.schemas import Order


class DecoyOrder(NamedTuple):
    merchant: str
    pickup_address: str
    items: tuple[str, ...]


# Lo que ve en el señuelo quien ya fue desviado al consultar un pedido ajeno: comercio,
# artículos y origen fabricados, para no exponer los del entorno protegido. Hay dos comercios
# por ciudad, y la ciudad es la última parte del origen. Las direcciones usan el mismo estilo
# ficticio que las reales, para no delatar el señuelo.
HONEYPOT_ORDERS: tuple[DecoyOrder, ...] = (
    DecoyOrder(
        "Smash Burger Co. · Chacao",
        "Av. Simulada 7, C.C. Ensayo, local 12, Chacao, Caracas",
        ("Hamburguesa clásica x2", "Papas fritas", "Refresco 355 ml"),
    ),
    DecoyOrder(
        "Excelsior Gama · Los Dos Caminos",
        "Av. Ficticia 3, C.C. Prueba, Los Dos Caminos, Caracas",
        ("Arroz Mary 1 kg x2", "Pasta Primor 1 kg", "Azúcar"),
    ),
    DecoyOrder(
        "Napoli Express · La Viña",
        "Av. Prueba 52, local 4, La Viña, Valencia",
        ("Pizza margarita mediana", "Pan de ajo"),
    ),
    DecoyOrder(
        "Heladería Copa Fría · Los Mangos",
        "Calle Prueba 64, local 2, Los Mangos, Valencia",
        ("Barquilla doble", "Merengada de fresa"),
    ),
    DecoyOrder(
        "Pollos La Granja · Naguanagua",
        "Av. Laboratorio 210, local 1, Naguanagua, Carabobo",
        ("Medio pollo a la brasa", "Yuca frita", "Refresco 1,5 L"),
    ),
    DecoyOrder(
        "Wasabi Lounge · San Diego",
        "Av. Sintética 95, local 2, San Diego, Carabobo",
        ("Roll California (10 pzs)", "Edamame"),
    ),
    DecoyOrder(
        "Locatel · La Lago",
        "Av. Ensayo 18, local 7, La Lago, Maracaibo",
        ("Ibuprofeno 400 mg (10 tab)", "Tapabocas (50 und)"),
    ),
    DecoyOrder(
        "Patacones del Lago · Santa Rita",
        "Av. Réplica 33, local 9, Santa Rita, Maracaibo",
        ("Patacón maracucho", "Chicha 500 ml"),
    ),
)

# Zonas donde vive un cliente en el señuelo, por ciudad de sus comercios señuelo.
DECOY_ZONES: dict[str, tuple[str, ...]] = {
    "Caracas": ("El Rosal", "Sebucán"),
    "Valencia": ("Los Mangos", "La Viña"),
    "Carabobo": ("Naguanagua", "San Diego"),
    "Maracaibo": ("La Lago", "Santa Rita"),
}

# Campos que el señuelo fabrica; el resto del pedido (ID, cliente, estado, total) es el mismo.
FABRICATED_FIELDS: tuple[str, ...] = (
    "customer_name",
    "customer_email",
    "merchant",
    "pickup_address",
    "delivery_address",
    "items",
)


def city_of(address: str) -> str:
    return address.rsplit(", ", 1)[1]


def decoy_delivery_address(customer_id: str) -> str:
    """Destino fabricado del cliente, el mismo en todos sus pedidos del señuelo."""
    seed = zlib.crc32(f"destino|{customer_id}".encode())
    cities = tuple(DECOY_ZONES)
    city = cities[seed % len(cities)]
    zones = DECOY_ZONES[city]
    zone = zones[seed // len(cities) % len(zones)]
    return f"Calle Réplica {10 + seed % 89}, Res. Ensayo, piso {1 + seed % 9}, {zone}, {city}"


def _order_number(order_id: str) -> int:
    digits = order_id.rsplit("-", 1)[-1]
    return int(digits) if digits.isdigit() else zlib.crc32(order_id.encode())


def _differs(decoy: DecoyOrder, order: Order) -> bool:
    return decoy.merchant != order.merchant and decoy.pickup_address != order.pickup_address


def honeypot_order(order: Order) -> Order:
    """Devuelve el pedido señuelo estable para `order`, sin datos del comercio ni del cliente.

    El nombre, el correo y el destino fabricados dependen del `customer_id`, no del pedido:
    todos los pedidos de un cliente muestran la misma identidad falsa y la misma dirección, y
    sus comercios son de la ciudad de esa dirección.
    """
    name, email = decoy_identity(order.customer_id)
    delivery = decoy_delivery_address(order.customer_id)
    if delivery == order.delivery_address:
        raise ValueError("El destino señuelo coincide con el real.")
    choices = [d for d in HONEYPOT_ORDERS if city_of(d.pickup_address) == city_of(delivery)]
    # Pedidos consecutivos de un cliente alternan entre los comercios señuelo de su ciudad.
    start = (zlib.crc32(order.customer_id.encode()) + _order_number(order.order_id)) % len(choices)
    for offset in range(len(choices)):
        decoy = choices[(start + offset) % len(choices)]
        if _differs(decoy, order):
            identity = {"customer_name": name, "customer_email": email}
            update = {**decoy._asdict(), **identity, "delivery_address": delivery}
            return order.model_copy(update=update)
    raise ValueError("No hay un pedido señuelo distinto del real.")
