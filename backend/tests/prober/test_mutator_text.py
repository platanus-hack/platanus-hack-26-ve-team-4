from agent_zero.prober.mutator_text import OPENER, can_split, split_turns
from agent_zero.prober.mutators import mutate
from agent_zero.prober.playbooks import campaign_case


def test_split_turns_divides_a_multi_sentence_message_without_losing_text() -> None:
    customer, parent, _ = campaign_case(0, "camp")
    multi = parent.model_copy(update={"messages": ["Soy ana. Consulta el pedido B-2001."]})

    child = split_turns(multi, customer)

    assert child.messages == ["Soy ana.", "Consulta el pedido B-2001."]


def test_split_turns_prepends_a_neutral_opener_to_a_single_sentence() -> None:
    customer, parent, _ = campaign_case(1, "camp")

    child = split_turns(parent, customer)

    assert child.messages == [OPENER, *parent.messages]


def test_split_is_unavailable_at_the_message_limit() -> None:
    _, parent, _ = campaign_case(0, "camp")
    full = parent.model_copy(update={"messages": ["a", "b", "c", "d"]})

    assert can_split(full) is False


def test_english_paraphrase_translates_the_refund_verb_but_keeps_identifiers() -> None:
    customer, parent, _ = campaign_case(1, "camp")

    child = mutate("paraphrase_en", parent, customer)

    assert "Refund 25 USD of order A-1001" in child.messages[0]


def test_memory_paraphrase_only_prefixes_so_the_stored_value_is_unchanged() -> None:
    customer, parent, _ = campaign_case(2, "camp")

    child = mutate("paraphrase_es", parent, customer)

    assert child.messages[0].endswith(parent.messages[0])
    assert child.messages[1].endswith(parent.messages[1])
