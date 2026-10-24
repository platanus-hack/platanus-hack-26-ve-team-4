import pytest

from agent_zero.llm.quota import InMemoryCallQuota


def test_reservation_is_all_or_nothing() -> None:
    quota = InMemoryCallQuota()
    assert quota.reserve([("day", 5), ("session", 1)]) is None

    exceeded = quota.reserve([("day", 5), ("session", 1)])

    assert exceeded == "session"
    assert quota.calls("day") == 1


def test_tokens_accumulate_per_key() -> None:
    quota = InMemoryCallQuota()

    quota.add_tokens("campaign:a", 100)
    quota.add_tokens("campaign:a", 50)

    assert quota.tokens("campaign:a") == 150
    assert quota.tokens("campaign:b") == 0


def test_negative_tokens_are_rejected() -> None:
    with pytest.raises(ValueError, match="negativo"):
        InMemoryCallQuota().add_tokens("campaign:a", -1)
