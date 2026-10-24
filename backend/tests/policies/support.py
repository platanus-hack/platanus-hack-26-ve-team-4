"""Project a stored policy version onto the `PolicyCandidate` contract.

The serialized `PolicyVersion` (`policy_view`) has no `policy_id`, no `scope` and no action
per rule, and it carries fields the contract forbids (`extra="forbid"`). This projection copies
only what the row holds and derives the rest explicitly:

- `policy_id`: `policy-NNNN` from the version number, as in the architecture example.
- `scope`: the tool of the finding that produced the candidate.
- `on_failure`: `block`, because the policy engine denies the call when a validator fails.
"""

from typing import Any

from agent_zero.policies.models import FailureAction

FIELDS_FROM_ROW = ("parent_version", "finding_ids", "reason", "status")


def as_policy_candidate(view: dict[str, Any], scope: str) -> dict[str, Any]:
    return {
        "policy_id": f"policy-{view['version']:04d}",
        "scope": scope,
        "rules": [
            {"validator": rule, "on_failure": FailureAction.BLOCK.value} for rule in view["rules"]
        ],
        **{field: view[field] for field in FIELDS_FROM_ROW},
    }
