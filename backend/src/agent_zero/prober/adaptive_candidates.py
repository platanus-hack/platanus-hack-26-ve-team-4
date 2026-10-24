import hashlib
from dataclasses import dataclass

from agent_zero.prober.mutators import MUTATORS, mutate
from agent_zero.prober.playbooks import campaign_case, case_digest
from agent_zero.prober.schemas import AttackCase
from agent_zero.prober.strategy_selector import Arm

OBJECTIVES = ("OBJ-ORDER", "OBJ-REFUND", "OBJ-MEMORY")
SEED_ARM = "seed"
PLAYBOOK_CASES = 30


@dataclass(frozen=True)
class Candidate:
    customer: str
    case: AttackCase
    digest: str


def all_arms() -> list[Arm]:
    return [(objective, name) for objective in OBJECTIVES for name in (SEED_ARM, *MUTATORS)]


def version_digest(digest: str, version: int) -> str:
    return hashlib.sha256(f"{digest}|v{version}".encode()).hexdigest()


def candidate(
    arm: Arm, campaign_id: str, index: int, version: int, seen: set[str]
) -> Candidate | None:
    objective, mutator = arm
    for playbook in range(PLAYBOOK_CASES):
        customer, parent, _ = campaign_case(playbook, campaign_id)
        if parent.objective_id != objective:
            continue
        if mutator == SEED_ARM:
            case = parent
        elif MUTATORS[mutator].applies(parent):
            case = mutate(mutator, parent.model_copy(update={"seed": index}), customer)
        else:
            continue
        case = case.model_copy(
            update={
                "case_id": f"{campaign_id}-{index}",
                "seed": index,
                "parent_case_id": f"playbook-{playbook}" if mutator != SEED_ARM else None,
            }
        )
        digest = version_digest(case_digest(customer, case), version)
        if digest not in seen:
            return Candidate(customer, case, digest)
    return None
