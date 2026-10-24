import pytest
from pydantic import ValidationError

from agent_zero.policies.models import PolicyStatus
from agent_zero.policies.schemas import PolicyCandidate

ARCHITECTURE_EXAMPLE = {
    "policy_id": "policy-0007",
    "parent_version": 6,
    "finding_ids": ["finding-0012"],
    "scope": "get_order",
    "rules": [{"validator": "order_belongs_to_session_customer", "on_failure": "block"}],
    "reason": "La consulta de un pedido debe respetar la identidad de la sesión",
    "status": "candidate",
}


def test_architecture_contract_example_parses() -> None:
    candidate = PolicyCandidate.model_validate(ARCHITECTURE_EXAMPLE)

    assert candidate.status is PolicyStatus.CANDIDATE


def test_candidate_scope_must_be_a_known_tool() -> None:
    with pytest.raises(ValidationError):
        PolicyCandidate.model_validate({**ARCHITECTURE_EXAMPLE, "scope": "run_shell"})
