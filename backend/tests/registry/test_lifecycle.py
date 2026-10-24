import pytest

from agent_zero.registry.errors import InvalidTransitionError
from agent_zero.registry.lifecycle import transition
from agent_zero.registry.models import VersionStatus


@pytest.mark.requirement("REG-03")
def test_allows_draft_to_approved_to_deprecated() -> None:
    assert transition(VersionStatus.DRAFT, VersionStatus.APPROVED) is VersionStatus.APPROVED
    assert transition(VersionStatus.APPROVED, VersionStatus.DEPRECATED) is VersionStatus.DEPRECATED


@pytest.mark.requirement("REG-03")
@pytest.mark.parametrize(
    ("current", "target"),
    [
        (VersionStatus.DRAFT, VersionStatus.DEPRECATED),
        (VersionStatus.APPROVED, VersionStatus.DRAFT),
        (VersionStatus.DEPRECATED, VersionStatus.APPROVED),
        (VersionStatus.DEPRECATED, VersionStatus.DRAFT),
        (VersionStatus.APPROVED, VersionStatus.APPROVED),
    ],
)
def test_rejects_other_transitions(current: VersionStatus, target: VersionStatus) -> None:
    with pytest.raises(InvalidTransitionError, match="Transición no permitida"):
        transition(current, target)
