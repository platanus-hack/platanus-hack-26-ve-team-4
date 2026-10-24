from agent_zero.policies.models import PolicyStatus

ALLOWED_TRANSITIONS: dict[PolicyStatus, frozenset[PolicyStatus]] = {
    PolicyStatus.CANDIDATE: frozenset({PolicyStatus.VALIDATING, PolicyStatus.REJECTED}),
    PolicyStatus.VALIDATING: frozenset({PolicyStatus.ACTIVE, PolicyStatus.REJECTED}),
    PolicyStatus.ACTIVE: frozenset({PolicyStatus.SUPERSEDED, PolicyStatus.ROLLED_BACK}),
    PolicyStatus.SUPERSEDED: frozenset(),
    PolicyStatus.REJECTED: frozenset(),
    PolicyStatus.ROLLED_BACK: frozenset(),
}


class InvalidPolicyTransitionError(ValueError):
    def __init__(self, current: PolicyStatus, target: PolicyStatus) -> None:
        super().__init__(f"Transición no permitida: {current.value} → {target.value}")
        self.current = current
        self.target = target


def transition(current: PolicyStatus, target: PolicyStatus) -> PolicyStatus:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidPolicyTransitionError(current, target)
    return target
