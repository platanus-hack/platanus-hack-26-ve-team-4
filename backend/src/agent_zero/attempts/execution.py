"""Puntos de conexión del intento con dominios que aún no existen.

`target` lo registra la víctima (#5), `evaluator` los oráculos (#8) y `policy_version` el
registro de políticas (#11). Sin `target` la API responde 503; sin `evaluator` un intento
terminado queda `inconclusive`, porque no hay veredicto que publicar.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from agent_zero.attempts.models import AttemptOutcome
from agent_zero.routing.models import Route

ARENA_ATTEMPT_HANDLER = "arena_attempt"


@dataclass(frozen=True)
class ArenaTarget:
    """Agente aprobado y handler del runtime que ejecutan un intento de la arena.

    El handler recibe como `input` un dict con `attempt_id`, `session_id`, `customer_id`,
    `messages`, `objective_id`, `policy_version` y `route`. Si su salida trae `reply` (str),
    es la respuesta que ve el participante.
    """

    agent_id: str
    agent_version: str
    handler: str = ARENA_ATTEMPT_HANDLER


@dataclass(frozen=True)
class EvaluationInput:
    attempt_id: str
    session_id: str
    objective_id: str | None
    policy_version: int
    route: Route
    run_id: str
    output: dict[str, Any] | None


class AttemptEvaluator(Protocol):
    async def evaluate(self, attempt: EvaluationInput) -> AttemptOutcome: ...


@dataclass
class ArenaWiring:
    target: ArenaTarget | None = None
    evaluator: AttemptEvaluator | None = None
    policy_version: Callable[[], int] = field(default=lambda: 0)
