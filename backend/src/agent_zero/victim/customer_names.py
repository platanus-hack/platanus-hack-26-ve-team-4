import unicodedata
import zlib

# Nombres de laboratorio: combinaciones comunes en Venezuela, ficticias y sin personas
# reconocibles. Ninguna lista repite los nombres ni los apellidos de los clientes semilla
# (Ana Rojas, Bruno Díaz, Carla Méndez), así que ningún `cust-demo-*` coincide con ellos.
FIRST_NAMES: tuple[str, ...] = (
    "María",
    "José",
    "Luis",
    "Carmen",
    "Carlos",
    "Rosa",
    "Pedro",
    "Gabriela",
    "Miguel",
    "Daniela",
    "Jesús",
    "Andreína",
    "Rafael",
    "Valentina",
    "Jorge",
    "Mariana",
    "Ricardo",
    "Patricia",
    "Alejandro",
    "Yolanda",
)

LAST_NAMES: tuple[str, ...] = (
    "González",
    "Rodríguez",
    "Pérez",
    "Hernández",
    "García",
    "Martínez",
    "López",
    "Sánchez",
    "Ramírez",
    "Torres",
    "Flores",
    "Rivas",
    "Morales",
    "Castillo",
    "Medina",
    "Romero",
    "Guerrero",
    "Silva",
    "Contreras",
    "Rangel",
)

# Nombres del señuelo: listas disjuntas de las reales, para que un nombre fabricado nunca
# coincida con el de ningún cliente del entorno protegido.
DECOY_FIRST_NAMES: tuple[str, ...] = (
    "Luisa",
    "Héctor",
    "Beatriz",
    "Óscar",
    "Elena",
    "Manuel",
    "Isabel",
    "Raúl",
    "Teresa",
    "Víctor",
)

DECOY_LAST_NAMES: tuple[str, ...] = (
    "Suárez",
    "Vargas",
    "Acosta",
    "Peña",
    "Salazar",
    "Blanco",
    "Mora",
    "Paredes",
    "Ortega",
    "Delgado",
)

EMAIL_DOMAIN = "correo-demo.ve"
DEMO_PREFIX = "cust-demo-"


def demo_customer_name(number: int) -> str:
    """Nombre determinista de `cust-demo-{number}`: único para los números menores de 400."""
    first = FIRST_NAMES[number % len(FIRST_NAMES)]
    last = LAST_NAMES[number // len(FIRST_NAMES) % len(LAST_NAMES)]
    return f"{first} {last}"


def customer_email(name: str, number: int | None = None) -> str:
    """`nombre.apellido{número}@correo-demo.ve`, en ASCII para que Model Armor lo reconozca."""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    local = ".".join(ascii_name.casefold().split())
    return f"{local}{'' if number is None else number}@{EMAIL_DOMAIN}"


def demo_number(customer_id: str) -> int | None:
    if not customer_id.startswith(DEMO_PREFIX):
        return None
    return int(customer_id.removeprefix(DEMO_PREFIX))


def decoy_identity(customer_id: str) -> tuple[str, str]:
    """Nombre y correo fabricados para el señuelo, los mismos en todos los pedidos del cliente."""
    seed = zlib.crc32(customer_id.encode())
    first = DECOY_FIRST_NAMES[seed % len(DECOY_FIRST_NAMES)]
    last = DECOY_LAST_NAMES[seed // len(DECOY_FIRST_NAMES) % len(DECOY_LAST_NAMES)]
    name = f"{first} {last}"
    return name, customer_email(name, demo_number(customer_id))
