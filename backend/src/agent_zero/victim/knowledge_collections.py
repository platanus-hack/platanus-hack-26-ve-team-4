"""Qué colecciones de la base de conocimiento ve cada entorno (decisión AGENT_ZERO-D-05)."""

# `oficial`: información pública de Yummi. `laboratorio`: reglas del escenario, como el límite de
# 20 USD. `senuelo`: políticas inventadas, coherentes con los pedidos fabricados del señuelo.
COLLECTIONS: tuple[str, ...] = ("oficial", "laboratorio", "senuelo")

TRUST_BY_COLLECTION: dict[str, str] = {
    "oficial": "official",
    "laboratorio": "lab",
    "senuelo": "decoy",
}

# El señuelo nunca ve las reglas del laboratorio; protegido y validación nunca ven el señuelo.
COLLECTIONS_BY_ENVIRONMENT: dict[str, tuple[str, ...]] = {
    "protected": ("oficial", "laboratorio"),
    "validation": ("oficial", "laboratorio"),
    "honeypot": ("oficial", "senuelo"),
}


def collections_for(environment: str) -> tuple[str, ...]:
    try:
        return COLLECTIONS_BY_ENVIRONMENT[environment]
    except KeyError:
        raise ValueError("Entorno sin colecciones de conocimiento.") from None
