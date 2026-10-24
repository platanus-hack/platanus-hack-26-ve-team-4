import pytest

from agent_zero.policies.lifecycle import InvalidPolicyTransitionError, transition
from agent_zero.policies.models import PolicyStatus


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (PolicyStatus.CANDIDATE, PolicyStatus.VALIDATING),
        (PolicyStatus.VALIDATING, PolicyStatus.ACTIVE),
        (PolicyStatus.VALIDATING, PolicyStatus.REJECTED),
        (PolicyStatus.ACTIVE, PolicyStatus.SUPERSEDED),
        (PolicyStatus.ACTIVE, PolicyStatus.ROLLED_BACK),
    ],
)
def test_allowed_transitions(current: PolicyStatus, target: PolicyStatus) -> None:
    assert transition(current, target) is target


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (PolicyStatus.CANDIDATE, PolicyStatus.ACTIVE),
        (PolicyStatus.REJECTED, PolicyStatus.VALIDATING),
        (PolicyStatus.ROLLED_BACK, PolicyStatus.ACTIVE),
    ],
)
def test_candidate_cannot_skip_validation_or_revive(
    current: PolicyStatus, target: PolicyStatus
) -> None:
    with pytest.raises(InvalidPolicyTransitionError):
        transition(current, target)
