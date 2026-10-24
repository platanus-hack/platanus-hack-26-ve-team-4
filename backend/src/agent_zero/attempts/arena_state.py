from pydantic import BaseModel

from agent_zero.attempts.models import AttemptOutcome, AttemptStatus

APPARENT = (AttemptOutcome.CONFIRMED_VIOLATION, AttemptOutcome.CONTAINED_HONEYPOT)


class ArenaState(BaseModel):
    """Contadores públicos de la ronda, ya saneados para la pantalla proyectada.

    Las violaciones confirmadas y los éxitos en el señuelo se suman en `apparent_successes`
    hasta la revelación (#13), para no delatar la ruta. `findings_open` es `None` mientras no
    exista el registro de hallazgos (#9): sin dato, no cero.
    """

    accepting: bool
    policy_version: int
    attempts_total: int
    queued: int
    running: int
    finished: int
    apparent_successes: int
    prevented: int
    not_achieved: int
    inconclusive: int
    findings_open: int | None


def arena_state(
    tally: dict[tuple[AttemptStatus, AttemptOutcome | None], int], policy_version: int
) -> ArenaState:
    def by_status(*statuses: AttemptStatus) -> int:
        return sum(count for (status, _), count in tally.items() if status in statuses)

    def by_outcome(*outcomes: AttemptOutcome) -> int:
        return sum(count for (_, outcome), count in tally.items() if outcome in outcomes)

    return ArenaState(
        accepting=True,
        policy_version=policy_version,
        attempts_total=sum(tally.values()),
        queued=by_status(AttemptStatus.QUEUED),
        running=by_status(AttemptStatus.RUNNING),
        finished=by_status(AttemptStatus.EVALUATED, AttemptStatus.INCONCLUSIVE),
        apparent_successes=by_outcome(*APPARENT),
        prevented=by_outcome(AttemptOutcome.PREVENTED),
        not_achieved=by_outcome(AttemptOutcome.NOT_ACHIEVED),
        inconclusive=by_outcome(AttemptOutcome.INCONCLUSIVE),
        findings_open=None,
    )
