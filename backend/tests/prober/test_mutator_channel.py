from agent_zero.prober.models import AttackFamily, Surface
from agent_zero.prober.mutators import mutate
from agent_zero.prober.playbooks import campaign_case


def test_document_channel_moves_the_instruction_into_a_lab_fixture() -> None:
    customer, parent, _ = campaign_case(1, "camp")

    child = mutate("channel_document", parent, customer)

    assert child.surface is Surface.DOCUMENT
    assert child.family is AttackFamily.INDIRECT_INJECTION
    assert child.fixture is not None
    assert child.fixture.surface == "document"
    assert child.fixture.source == "lab:campaign"
    assert parent.messages[-1] in child.fixture.content
    assert parent.messages[-1] not in child.messages


def test_tool_result_channel_is_labelled_as_tool_poisoning() -> None:
    customer, parent, _ = campaign_case(0, "camp")

    child = mutate("channel_tool_result", parent, customer)

    assert child.surface is Surface.TOOL_RESULT
    assert child.family is AttackFamily.TOOL_POISONING
    assert child.fixture is not None
    assert child.fixture.surface == "tool_result"


def test_memory_instruction_is_the_first_message_and_closes_the_document() -> None:
    customer, parent, _ = campaign_case(2, "camp")

    child = mutate("channel_document", parent, customer)

    assert child.fixture is not None
    assert child.fixture.content.endswith(parent.messages[0])


def test_chain_prepends_a_legitimate_query_about_the_customers_own_order() -> None:
    customer, parent, _ = campaign_case(0, "camp")

    child = mutate("chain", parent, customer)

    assert child.messages[1:] == parent.messages
    assert child.messages[0].startswith("Consulta el estado de mi pedido ")
    assert "B-2001" not in child.messages[0]
