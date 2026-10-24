import pytest
from pydantic import ValidationError

from agent_zero.identity.schemas import AgentGrant
from agent_zero.shared.classification import DataClassification


def test_scopes_are_sorted_and_deduplicated() -> None:
    grant = AgentGrant(
        agent_id="a",
        version="1",
        department="d",
        scopes=("tool:b", "memory:read", "tool:b"),
        clearance=DataClassification.PUBLIC,
    )
    assert grant.scopes == ("memory:read", "tool:b")


def test_invalid_scope_shape_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AgentGrant(
            agent_id="a",
            version="1",
            department="d",
            scopes=("todo",),
            clearance=DataClassification.PUBLIC,
        )
