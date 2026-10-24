from collections import Counter

import pytest
from pydantic import ValidationError

from agent_zero.evals.suite import evaluation_suite, fixture_hash, minimum_calls, suite_hash
from agent_zero.prober.models import AttackFamily, Surface
from agent_zero.prober.playbooks import campaign_case, case_digest
from agent_zero.prober.schemas import AttackCase, AttackMutation


def test_frozen_suite_covers_six_real_surfaces_and_has_no_duplicate_effective_inputs() -> None:
    cases = evaluation_suite()
    attacks = [case for case in cases if case.adversarial]
    legitimate = [case for case in cases if not case.adversarial]
    assert len(cases) == 45
    assert len(attacks) == 30
    assert len(legitimate) == 15
    assert Counter(case.family for case in attacks) == dict.fromkeys(AttackFamily, 5)
    assert Counter(case.partition for case in attacks) == {"discovery": 20, "reserved": 10}
    assert sum(case.critical for case in legitimate) == 5
    assert all(
        len(case.messages) > 1
        for case in attacks
        if case.family in {AttackFamily.GOAL_HIJACKING, AttackFamily.MEMORY_POISONING}
    )
    for case in attacks:
        if case.surface in {Surface.DOCUMENT, Surface.TOOL_RESULT}:
            assert case.fixture is not None
            assert case.fixture.surface == case.surface.value
            assert case.fixture.source == "lab:evaluation"
    assert len({campaign_case(index, "first")[2] for index in range(30)}) == 30
    assert [campaign_case(index, "first")[2] for index in range(30)] == [
        campaign_case(index, "second")[2] for index in range(30)
    ]
    assert suite_hash(cases) == suite_hash(evaluation_suite())
    assert len(fixture_hash()) == 64
    assert minimum_calls(cases, 3) == 672


def test_deduplication_ignores_case_labels_identity_is_a_server_boundary() -> None:
    customer, original, digest = campaign_case(0, "first")
    renamed = original.model_copy(
        update={
            "case_id": "other",
            "family": AttackFamily.GOAL_HIJACKING,
            "surface": Surface.MEMORY,
            "seed": 100,
            "messages": [original.messages[0].upper()],
        }
    )
    assert case_digest(customer, renamed) == digest
    assert case_digest("cust-bruno", renamed) != digest


@pytest.mark.parametrize(
    "extra",
    [
        {"policy_version": 0},
        {"customer_id": "cust-bruno"},
        {"rules": []},
        {"objective_id": "OBJ-ORDER"},
    ],
)
def test_mutator_cannot_choose_privileges_identity_version_or_verdict(
    extra: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        AttackMutation.model_validate({"messages": ["Consulta A-1001"], **extra})


def test_declared_surface_requires_the_actual_fixture_not_just_a_label() -> None:
    _, direct, _ = campaign_case(0, "first")
    with pytest.raises(ValidationError, match="fixture controlado"):
        AttackCase.model_validate(direct.model_dump() | {"surface": "document"})
