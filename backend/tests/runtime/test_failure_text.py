import pytest

from agent_zero.runtime.failure_text import MAX_FAILURE_LENGTH, safe_failure_text


@pytest.mark.requirement("OBS-03")
def test_pii_is_redacted_from_failure_text() -> None:
    text = safe_failure_text("falla con cliente@example.com tarjeta 4111 1111 1111 1111")
    assert "example.com" not in text
    assert "4111" not in text
    assert "[EMAIL]" in text
    assert "[CARD]" in text


def test_failure_text_is_bounded() -> None:
    assert len(safe_failure_text("x" * 5000)) == MAX_FAILURE_LENGTH
