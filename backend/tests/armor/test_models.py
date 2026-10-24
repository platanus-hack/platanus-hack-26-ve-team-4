from agent_zero.armor.models import POISONING_SURFACES, TOOL_SURFACES, PiiKind, Surface


def test_pii_tags_match_contract() -> None:
    assert [kind.tag for kind in PiiKind] == ["[EMAIL]", "[PHONE]", "[CARD]", "[RUT]", "[CEDULA]"]


def test_pii_descriptions_are_spanish() -> None:
    assert PiiKind.RUT.description == "RUT chileno"
    assert all(kind.description for kind in PiiKind)


def test_tool_surfaces_are_subset_of_poisoning_surfaces() -> None:
    assert TOOL_SURFACES < POISONING_SURFACES
    assert Surface.MEMORY_WRITE in POISONING_SURFACES
    assert Surface.USER_INPUT not in POISONING_SURFACES
