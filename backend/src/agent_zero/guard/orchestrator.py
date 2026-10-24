from agent_zero.contract.conditions import CallFacts
from agent_zero.contract.schema import DomainContract
from agent_zero.guard.check_service import GuardCheckService
from agent_zero.guard.learning_service import GuardLearningService
from agent_zero.guard.schemas import CheckRequest, Decision

INVARIANT_PREFIX = "invariant:"


async def guarded_check(
    checks: GuardCheckService,
    learning: GuardLearningService,
    contract: DomainContract,
    request: CheckRequest,
) -> Decision:
    decision = await checks.check(contract, request)
    if not (decision.rule_id or "").startswith(INVARIANT_PREFIX):
        return decision
    facts = CallFacts(
        request.tool, request.arguments, request.subject, decision.provenance, request.owners
    )
    learned = await learning.learn_from_blocked(
        contract, decision.call_id, facts, decision.policy_version
    )
    return decision.model_copy(update={"learned": learned})
