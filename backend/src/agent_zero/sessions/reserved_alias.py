"""Prefijos de alias reservados: el enjambre de agentes simulados y los chats de prueba del equipo.

El tablero rotula como "Agente simulado" a las sesiones cuyo alias empieza con `SWARM_PREFIX`, y
como "Prueba interna" a las que empiezan con `TEST_PREFIX` (chat interno de Operación). Para que el
público no pueda hacerse pasar por ninguno de los dos, `POST /api/sessions` solo acepta esos
prefijos con el secreto de operador.
"""

SWARM_PREFIX = "Agente-"
TEST_PREFIX = "Interno-"
RESERVED_PREFIXES = (SWARM_PREFIX, TEST_PREFIX)


def is_reserved_alias(alias: str) -> bool:
    """Sin distinguir mayúsculas ni espacios iniciales: más amplio que la clasificación."""
    folded = alias.strip().casefold()
    return any(folded.startswith(prefix.casefold()) for prefix in RESERVED_PREFIXES)


def is_test_alias(alias: str) -> bool:
    """Exacto, como la clasificación del tablero: sin ignorar mayúsculas ni espacios."""
    return alias.startswith(TEST_PREFIX)
