from agent_zero.prober.adaptive_candidates import (
    OBJECTIVES,
    SEED_ARM,
    all_arms,
    candidate,
    version_digest,
)
from agent_zero.prober.mutators import MUTATORS


def test_arms_cover_every_objective_with_the_seed_and_every_mutator() -> None:
    arms = all_arms()

    assert len(arms) == len(OBJECTIVES) * (1 + len(MUTATORS))
    assert {mutator for _, mutator in arms} == {SEED_ARM, *MUTATORS}


def test_every_arm_has_a_candidate_for_its_objective() -> None:
    for arm in all_arms():
        found = candidate(arm, "camp", 4, 0, set())
        if found is None:
            continue
        assert found.case.objective_id == arm[0]
        assert found.case.case_id == "camp-4"
        assert found.case.mutator == (None if arm[1] == SEED_ARM else arm[1])


def test_seed_arm_replays_the_playbooks_and_never_repeats_a_digest() -> None:
    seen: set[str] = set()
    for index in range(40):
        found = candidate(("OBJ-REFUND", SEED_ARM), "camp", index, 0, seen)
        if found is None:
            break
        assert found.digest not in seen
        seen.add(found.digest)

    assert 0 < len(seen) <= 30


def test_digest_is_scoped_by_policy_version_so_exploits_can_be_retested() -> None:
    first = candidate(("OBJ-ORDER", SEED_ARM), "camp", 0, 0, set())
    assert first is not None
    again_same_version = candidate(("OBJ-ORDER", SEED_ARM), "camp", 1, 0, {first.digest})
    next_version = candidate(("OBJ-ORDER", SEED_ARM), "camp", 1, 1, {first.digest})

    assert again_same_version is not None
    assert again_same_version.digest != first.digest
    assert next_version is not None
    assert next_version.digest != first.digest
    assert next_version.case.messages == first.case.messages
    assert version_digest("x", 0) != version_digest("x", 1)


def test_candidates_are_reproducible() -> None:
    arm = ("OBJ-MEMORY", "paraphrase_es")

    assert candidate(arm, "camp", 7, 2, set()) == candidate(arm, "camp", 7, 2, set())
