import pytest

from agent_zero.victim.environments import ENVIRONMENTS
from agent_zero.victim.knowledge_collections import (
    COLLECTIONS,
    COLLECTIONS_BY_ENVIRONMENT,
    TRUST_BY_COLLECTION,
    collections_for,
)


def test_every_collection_has_a_trust_level() -> None:
    assert set(TRUST_BY_COLLECTION) == set(COLLECTIONS)
    assert len(set(TRUST_BY_COLLECTION.values())) == len(COLLECTIONS)


def test_every_execution_environment_has_its_collections() -> None:
    assert set(COLLECTIONS_BY_ENVIRONMENT) == {*ENVIRONMENTS, "validation"}


def test_the_decoy_and_the_lab_rules_never_meet() -> None:
    assert "laboratorio" not in collections_for("honeypot")
    assert "senuelo" not in collections_for("protected")
    assert "senuelo" not in collections_for("validation")
    assert collections_for("protected") == collections_for("validation")
    assert all("oficial" in collections_for(name) for name in COLLECTIONS_BY_ENVIRONMENT)


def test_an_unknown_environment_has_no_collections() -> None:
    with pytest.raises(ValueError, match="colecciones"):
        collections_for("validation-1234")
