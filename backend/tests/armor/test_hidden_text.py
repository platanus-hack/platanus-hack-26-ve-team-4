import pytest

from agent_zero.armor.hidden_text import (
    decode_tag_characters,
    has_invisible_run,
    has_tag_characters,
)
from tests.armor.hidden_attacks import to_tag_chars


@pytest.mark.requirement("ARM-01")
def test_tag_characters_are_detected_and_decoded() -> None:
    hidden = "Hola" + to_tag_chars("ignore all")
    assert has_tag_characters(hidden)
    assert decode_tag_characters(hidden) == "ignore all"


@pytest.mark.requirement("ARM-04")
def test_plain_text_and_flag_sequences_are_clean() -> None:
    flag = "\U0001f3f4" + to_tag_chars("gbeng") + "\U000e007f"
    assert not has_tag_characters("Hola mundo")
    assert not has_tag_characters(f"Gol {flag}")
    assert decode_tag_characters("Hola mundo") is None


@pytest.mark.requirement("ARM-01")
def test_invisible_runs_need_several_characters() -> None:
    assert has_invisible_run("a\u200b\u200b\u200b\u200bb")
    assert not has_invisible_run("a\u200bb")
    assert not has_invisible_run("texto normal")
