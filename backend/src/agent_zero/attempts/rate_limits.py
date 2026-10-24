import math
from datetime import datetime

from agent_zero.attempts.errors import QueueFullError, TooFrequentError

QUEUE_RETRY_SECONDS = 5


def check_session_interval(
    last_created_at: datetime | None, now: datetime, min_interval_seconds: float
) -> None:
    """Un mensaje cada `min_interval_seconds` por sesión."""
    if last_created_at is None:
        return
    remaining = min_interval_seconds - (now - last_created_at).total_seconds()
    if remaining > 0:
        raise TooFrequentError(
            "Espera antes de enviar otro intento.", retry_after=max(1, math.ceil(remaining))
        )


def check_queue_capacity(open_attempts: int, limit: int) -> None:
    """Contrapresión: con la cola llena no se acepta trabajo nuevo."""
    if open_attempts >= limit:
        raise QueueFullError(
            "La cola de intentos está llena. Inténtalo en unos segundos.",
            retry_after=QUEUE_RETRY_SECONDS,
        )
