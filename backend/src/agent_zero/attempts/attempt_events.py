from typing import Any

from agent_zero.attempts.models import Attempt
from agent_zero.attempts.schemas import public_outcome
from agent_zero.events.broker import EventBroker
from agent_zero.events.models import EventType, Visibility
from agent_zero.events.schemas import EventDraft


class AttemptEvents:
    """Cada transición sale dos veces: completa para operación y anónima para el público.

    La copia pública no lleva intento, sesión, ruta ni motivo, y el resultado pasa por
    `public_outcome` para no delatar el señuelo.
    """

    def __init__(self, broker: EventBroker) -> None:
        self._broker = broker

    def _publish(
        self, kind: EventType, attempt: Attempt, operator: dict[str, Any], public: dict[str, Any]
    ) -> None:
        self._broker.publish(
            EventDraft(
                type=kind,
                visibility=Visibility.OPERATOR,
                attempt_id=attempt.id,
                session_id=attempt.session_id,
                policy_version=attempt.policy_version,
                data=operator,
            )
        )
        self._broker.publish(
            EventDraft(
                type=kind,
                visibility=Visibility.PUBLIC,
                policy_version=attempt.policy_version,
                data=public,
            )
        )

    def queued(self, attempt: Attempt) -> None:
        self._publish(
            EventType.ATTEMPT_QUEUED,
            attempt,
            {
                "status": attempt.status.value,
                "origin": attempt.origin.value,
                "route": attempt.route.value,
            },
            {"status": attempt.status.value},
        )

    def started(self, attempt: Attempt) -> None:
        self._publish(
            EventType.ATTEMPT_STARTED,
            attempt,
            {"status": attempt.status.value, "run_id": attempt.run_id},
            {"status": attempt.status.value},
        )

    def finished(self, attempt: Attempt) -> None:
        operator: dict[str, Any] = {
            "status": attempt.status.value,
            "outcome": attempt.outcome.value if attempt.outcome else None,
        }
        if attempt.failure_reason:
            operator["reason"] = attempt.failure_reason
        self._publish(
            EventType.ATTEMPT_EVALUATED,
            attempt,
            operator,
            {"status": attempt.status.value, "outcome": public_outcome(attempt.outcome)},
        )
