"""Prefijo de alias reservado para el enjambre de agentes simulados.

El tablero rotula como "Agente simulado" a las sesiones cuyo alias empieza con este prefijo. Para
que el público no pueda hacerse pasar por el enjambre, `POST /api/sessions` solo lo acepta con el
secreto de operador.
"""

SWARM_PREFIX = "Agente-"


def is_reserved_alias(alias: str) -> bool:
    """Sin distinguir mayúsculas ni espacios iniciales: más amplio que la clasificación."""
    return alias.strip().casefold().startswith(SWARM_PREFIX.casefold())
