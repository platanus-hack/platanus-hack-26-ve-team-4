import pytest
from pydantic import ValidationError

from agent_zero.attempts.schemas import AttemptCreate, is_blank


@pytest.mark.parametrize("text", ["   ", "\n\t", "\u200b", "\u200b \ufeff", "\u2060\u200d"])
def test_invisible_messages_are_rejected(text: str) -> None:
    assert is_blank(text)
    with pytest.raises(ValidationError, match="vacíos"):
        AttemptCreate(messages=[text], idempotency_key="k")


@pytest.mark.parametrize(
    "text", ["🤔", "\U0001f469\u200d\U0001f4bb", "hola\n1) uno\n2) dos", "a\u200bb"]
)
def test_emoji_and_multiline_messages_are_accepted(text: str) -> None:
    assert AttemptCreate(messages=[text], idempotency_key="k").turns == [text]


def test_exactly_one_message_form_is_required() -> None:
    with pytest.raises(ValidationError):
        AttemptCreate(message="a", messages=["b"], idempotency_key="k")
    with pytest.raises(ValidationError):
        AttemptCreate(idempotency_key="k")
