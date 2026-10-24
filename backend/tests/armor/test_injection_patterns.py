import pytest

from agent_zero.armor.injection_patterns import INJECTION_PATTERNS
from agent_zero.armor.pattern_scanner import matching_labels
from tests.armor.attacks import OBFUSCATED_ATTACKS, PLAIN_ATTACKS
from tests.armor.legitimate import LEGITIMATE_MESSAGES


@pytest.mark.requirement("ARM-01")
@pytest.mark.parametrize("attack", PLAIN_ATTACKS)
def test_plain_attack_matches_a_pattern(attack: str) -> None:
    assert matching_labels(attack, INJECTION_PATTERNS)


@pytest.mark.requirement("ARM-01")
@pytest.mark.parametrize(("technique", "attack"), OBFUSCATED_ATTACKS)
def test_obfuscated_attack_matches_a_pattern(technique: str, attack: str) -> None:
    assert matching_labels(attack, INJECTION_PATTERNS), technique


@pytest.mark.requirement("ARM-04")
@pytest.mark.parametrize("message", LEGITIMATE_MESSAGES)
def test_legitimate_message_matches_no_pattern(message: str) -> None:
    assert matching_labels(message, INJECTION_PATTERNS) == []


def test_pattern_labels_are_unique() -> None:
    labels = [item.label for item in INJECTION_PATTERNS]
    assert len(labels) == len(set(labels))
