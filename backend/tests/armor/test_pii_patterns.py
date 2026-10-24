import pytest

from agent_zero.armor.pii_patterns import CEDULA, EMAIL, PHONE_PATTERNS, RUT
from tests.armor.pii_samples import CEDULAS, EMAILS, PHONES, VALID_RUTS


@pytest.mark.requirement("ARM-03")
@pytest.mark.parametrize("email", EMAILS)
def test_email_pattern(email: str) -> None:
    assert EMAIL.fullmatch(email)


@pytest.mark.requirement("ARM-03")
@pytest.mark.parametrize("phone", PHONES)
def test_phone_patterns(phone: str) -> None:
    assert any(regex.fullmatch(phone) for regex in PHONE_PATTERNS)


@pytest.mark.requirement("ARM-03")
@pytest.mark.parametrize("cedula", CEDULAS)
def test_cedula_pattern(cedula: str) -> None:
    assert CEDULA.fullmatch(cedula)


@pytest.mark.requirement("ARM-03")
@pytest.mark.parametrize("rut", VALID_RUTS)
def test_rut_pattern(rut: str) -> None:
    assert RUT.fullmatch(rut)


def test_cedula_needs_six_to_nine_digits() -> None:
    assert not CEDULA.search("V-12345")
    assert not CEDULA.search("V-1234567890")
