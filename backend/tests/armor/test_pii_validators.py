import pytest

from agent_zero.armor.pii_validators import is_valid_rut, passes_luhn, rut_check_digit
from tests.armor.pii_samples import INVALID_CARDS, INVALID_RUTS, VALID_CARDS, VALID_RUTS


@pytest.mark.requirement("ARM-03")
@pytest.mark.parametrize("card", VALID_CARDS)
def test_valid_cards_pass_luhn(card: str) -> None:
    assert passes_luhn(card)


@pytest.mark.requirement("ARM-03")
@pytest.mark.parametrize("card", INVALID_CARDS)
def test_invalid_cards_fail_luhn(card: str) -> None:
    assert not passes_luhn(card)


def test_luhn_rejects_short_and_repeated_digits() -> None:
    assert not passes_luhn("4111")
    assert not passes_luhn("0000000000000000")


@pytest.mark.requirement("ARM-03")
@pytest.mark.parametrize("rut", VALID_RUTS)
def test_valid_ruts(rut: str) -> None:
    assert is_valid_rut(rut)


@pytest.mark.requirement("ARM-03")
@pytest.mark.parametrize("rut", INVALID_RUTS)
def test_invalid_ruts(rut: str) -> None:
    assert not is_valid_rut(rut)


def test_rut_check_digit_k_and_zero() -> None:
    assert rut_check_digit("12345678") == "5"
    assert {rut_check_digit(str(n)) for n in range(1, 400)} >= {"K", "0"}


def test_rut_without_separator_is_invalid() -> None:
    assert not is_valid_rut("123456785")
