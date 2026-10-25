from agent_zero.victim.fixtures import ORDERS
from agent_zero.victim.honeytool_schemas import HONEYTOOL_DESCRIPTIONS
from agent_zero.victim.tool_schemas import DESCRIPTIONS, tool_specs


def test_no_tool_description_contains_a_fixture_order_id() -> None:
    texts = list((DESCRIPTIONS | HONEYTOOL_DESCRIPTIONS).values())
    texts += [spec["description"] for spec in tool_specs(decoy=True)]
    for order_id in ORDERS:
        assert not any(order_id in text for text in texts)


def test_get_order_description_is_neutral() -> None:
    assert "identificador" in DESCRIPTIONS["get_order"]
