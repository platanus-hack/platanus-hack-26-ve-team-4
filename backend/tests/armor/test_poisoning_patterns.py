import pytest

from agent_zero.armor.pattern_scanner import matching_labels
from agent_zero.armor.poisoning_patterns import POISONING_PATTERNS
from tests.armor.legitimate import LEGITIMATE_TOOL_TEXTS
from tests.armor.poisoning import POISONED_DESCRIPTIONS, POISONED_OUTPUTS


@pytest.mark.requirement("ARM-02")
@pytest.mark.parametrize("text", [*POISONED_DESCRIPTIONS, *POISONED_OUTPUTS])
def test_poisoned_text_matches_a_pattern(text: str) -> None:
    assert matching_labels(text, POISONING_PATTERNS)


@pytest.mark.requirement("ARM-04")
@pytest.mark.parametrize("text", LEGITIMATE_TOOL_TEXTS)
def test_legitimate_tool_text_matches_no_pattern(text: str) -> None:
    assert matching_labels(text, POISONING_PATTERNS) == []


def test_pattern_labels_are_unique() -> None:
    labels = [item.label for item in POISONING_PATTERNS]
    assert len(labels) == len(set(labels))
