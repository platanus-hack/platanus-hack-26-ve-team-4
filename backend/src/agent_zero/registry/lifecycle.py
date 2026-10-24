from agent_zero.registry.errors import InvalidTransitionError
from agent_zero.registry.models import VersionStatus

ALLOWED_TRANSITIONS: dict[VersionStatus, frozenset[VersionStatus]] = {
    VersionStatus.DRAFT: frozenset({VersionStatus.APPROVED}),
    VersionStatus.APPROVED: frozenset({VersionStatus.DEPRECATED}),
    VersionStatus.DEPRECATED: frozenset(),
}


def transition(current: VersionStatus, target: VersionStatus) -> VersionStatus:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidTransitionError(current.value, target.value)
    return target
