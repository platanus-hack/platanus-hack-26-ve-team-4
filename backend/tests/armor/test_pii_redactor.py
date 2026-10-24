import base64

import pytest

from agent_zero.armor.models import PiiKind
from agent_zero.armor.pii_redactor import redact_with_kinds
from tests.armor.pii_samples import (
    CEDULAS,
    EMAILS,
    EVASIVE_CARDS,
    EVASIVE_CEDULAS,
    EVASIVE_EMAILS,
    FULLWIDTH_AT,
    INVALID_CARDS,
    INVALID_RUTS,
    PHONES,
    VALID_CARDS,
    VALID_RUTS,
    ZERO_WIDTH_SPACE,
)


@pytest.mark.requirement("ARM-03")
@pytest.mark.parametrize(
    ("samples", "kind"),
    [
        (EMAILS, PiiKind.EMAIL),
        (PHONES, PiiKind.PHONE),
        (VALID_CARDS, PiiKind.CARD),
        (VALID_RUTS, PiiKind.RUT),
        (CEDULAS, PiiKind.CEDULA),
    ],
)
def test_each_type_is_redacted_with_its_tag(samples: tuple[str, ...], kind: PiiKind) -> None:
    for sample in samples:
        text, kinds = redact_with_kinds(f"Mi dato es {sample}, gracias.")
        assert text == f"Mi dato es {kind.tag}, gracias.", sample
        assert kinds == (kind,), sample


@pytest.mark.requirement("ARM-03")
@pytest.mark.parametrize("number", INVALID_CARDS)
def test_number_failing_luhn_is_not_a_card(number: str) -> None:
    text, kinds = redact_with_kinds(f"Referencia {number}")
    assert PiiKind.CARD not in kinds
    assert "[CARD]" not in text


@pytest.mark.requirement("ARM-03")
@pytest.mark.parametrize("rut", INVALID_RUTS)
def test_rut_with_wrong_check_digit_is_not_redacted(rut: str) -> None:
    assert redact_with_kinds(rut) == (rut, ())


@pytest.mark.requirement("ARM-03")
def test_multiple_types_in_one_text() -> None:
    text, kinds = redact_with_kinds(
        "Soy V-12345678, mi correo ana@tienda.cl y mi tarjeta 4111 1111 1111 1111"
    )
    assert text == "Soy [CEDULA], mi correo [EMAIL] y mi tarjeta [CARD]"
    assert set(kinds) == {PiiKind.CEDULA, PiiKind.EMAIL, PiiKind.CARD}


@pytest.mark.requirement("ARM-04")
def test_order_numbers_are_not_pii() -> None:
    text = "Mi pedido #48213 costó 24990 pesos, llegó el 2026-10-12."
    assert redact_with_kinds(text) == (text, ())


@pytest.mark.requirement("ARM-03", "MEM-03")
@pytest.mark.parametrize(
    ("samples", "kind"),
    [
        (EVASIVE_CARDS, PiiKind.CARD),
        (EVASIVE_CEDULAS, PiiKind.CEDULA),
        (EVASIVE_EMAILS, PiiKind.EMAIL),
    ],
)
def test_evasive_variants_are_still_redacted(samples: tuple[str, ...], kind: PiiKind) -> None:
    for sample in samples:
        text, kinds = redact_with_kinds(f"Mi dato es {sample}, gracias.")
        assert text == f"Mi dato es {kind.tag}, gracias.", repr(sample)
        assert kinds == (kind,), repr(sample)


@pytest.mark.requirement("ARM-03", "MEM-03")
def test_base64_encoded_email_is_redacted() -> None:
    encoded = base64.b64encode(b"contacto: cliente@example.com").decode()
    text, kinds = redact_with_kinds(f"adjunto {encoded} fin")
    assert text == "adjunto [EMAIL] fin"
    assert kinds == (PiiKind.EMAIL,)


@pytest.mark.requirement("ARM-04")
def test_text_without_pii_is_returned_untouched() -> None:
    original = f"Hola{ZERO_WIDTH_SPACE} mundo {FULLWIDTH_AT} sin datos, V 12 y e 5"
    assert redact_with_kinds(original) == (original, ())
