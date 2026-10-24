import json
import re

import pytest

from agent_zero.llm.demo_actions import follow_untrusted, propose
from agent_zero.prober.mutators import MUTATORS, applicable, mutate
from agent_zero.prober.playbooks import campaign_case, case_digest
from agent_zero.prober.schemas import AttackCase

ORDER_IDS = re.compile(r"\b[A-Z]-\d{4,9}\b")
ATTACK_TOOLS = {"get_order", "request_refund", "save_memory"}
SEEDS = [campaign_case(index, "camp") for index in range(6)]


def _order_ids(case: AttackCase) -> set[str]:
    text = " ".join(case.messages) + (case.fixture.content if case.fixture else "")
    return set(ORDER_IDS.findall(text))


def _cases() -> list[tuple[str, str, AttackCase]]:
    return [
        (name, customer, parent.model_copy(update={"seed": 3}))
        for customer, parent, _ in SEEDS
        for name in applicable(parent)
    ]


@pytest.mark.parametrize(("name", "customer", "parent"), _cases())
def test_each_mutator_keeps_objective_identifiers_and_validity(
    name: str, customer: str, parent: AttackCase
) -> None:
    child = mutate(name, parent, customer)

    assert child.objective_id == parent.objective_id
    assert child.fixture_id == parent.fixture_id
    assert child.origin == parent.origin
    assert child.mutator == name
    assert child.parent_case_id == parent.case_id
    assert _order_ids(parent) <= _order_ids(child)
    assert len(child.messages) <= 4
    assert all(len(message) <= 4000 for message in child.messages)
    assert case_digest(customer, child) != case_digest(customer, parent)


@pytest.mark.parametrize(("name", "customer", "parent"), _cases())
def test_mutators_are_deterministic(name: str, customer: str, parent: AttackCase) -> None:
    assert mutate(name, parent, customer) == mutate(name, parent, customer)


def test_seed_selects_a_different_template() -> None:
    customer, parent, _ = SEEDS[0]
    first = mutate("paraphrase_es", parent.model_copy(update={"seed": 0}), customer)
    second = mutate("paraphrase_es", parent.model_copy(update={"seed": 1}), customer)

    assert first.messages != second.messages


def test_channel_mutators_only_apply_to_fixture_free_cases() -> None:
    indirect = SEEDS[3][1]
    direct = SEEDS[0][1]

    assert "channel_document" not in applicable(indirect)
    assert "channel_tool_result" not in applicable(indirect)
    assert {"channel_document", "channel_tool_result"} <= set(applicable(direct))
    with pytest.raises(ValueError, match="no aplica"):
        mutate("channel_document", indirect, SEEDS[3][0])


def test_unknown_mutator_is_rejected() -> None:
    assert "nonexistent" not in MUTATORS
    with pytest.raises(KeyError):
        mutate("nonexistent", SEEDS[0][1], SEEDS[0][0])


def _tool_names(case: AttackCase) -> list[str]:
    names = [name for message in case.messages for name, _ in propose(message)]
    if case.fixture is not None:
        names += [name for name, _ in follow_untrusted([_untrusted(case.fixture.content)])]
    return names


def _untrusted(content: str) -> str:
    return json.dumps({"articles": [{"trust": "untrusted", "text": content}]})


@pytest.mark.parametrize(
    "name", ["paraphrase_es", "paraphrase_en", "channel_document", "channel_tool_result", "chain"]
)
def test_demo_interpreter_still_proposes_the_attack_action(name: str) -> None:
    for customer, parent, _ in SEEDS:
        if name not in applicable(parent):
            continue
        child = mutate(name, parent.model_copy(update={"seed": 2}), customer)
        if ATTACK_TOOLS & set(_tool_names(parent)):
            assert ATTACK_TOOLS & set(_tool_names(child)), (name, parent.family)
