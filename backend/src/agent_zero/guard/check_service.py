import uuid

from agent_zero.contract.conditions import CallFacts, NotOwner
from agent_zero.contract.provenance import label_arguments
from agent_zero.contract.schema import DomainContract
from agent_zero.guard.enforcement import first_denial
from agent_zero.guard.facts import dump
from agent_zero.guard.models import GuardCallRecord, GuardPolicyRecord
from agent_zero.guard.repository import IncompatiblePolicyError, active_policy, rules_of
from agent_zero.guard.schemas import CheckRequest, Decision
from agent_zero.shared.database import Database


def _undeclared(contract: DomainContract, request: CheckRequest) -> str | None:
    spec = contract.tools.get(request.tool)
    if spec is None:
        return "Herramienta no declarada en el contrato."
    extra = sorted(set(request.arguments) - set(spec.arguments))
    return f"Argumentos no declarados: {', '.join(extra)}." if extra else None


class GuardCheckService:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def check(self, contract: DomainContract, request: CheckRequest) -> Decision:
        segments: list[tuple[str, str]] = [(item.origin, item.text) for item in request.context]
        provenance = {**label_arguments(segments, request.arguments), **request.provenance}
        facts = CallFacts(
            request.tool, request.arguments, request.subject, provenance, request.owners
        )
        call_id = f"gc-{uuid.uuid4().hex[:20]}"
        async with self._database.sessions() as db, db.begin():
            record = await active_policy(db, contract.contract_id)
            version = record.version if record else 0
            rule_id, reason = self._decide(contract, request, record, facts)
            db.add(
                GuardCallRecord(
                    call_id=call_id,
                    contract_id=contract.contract_id,
                    tool=request.tool,
                    subject=request.subject,
                    facts=dump(facts),
                    allowed=rule_id is None,
                    rule_id=rule_id,
                    policy_version=version,
                )
            )
        return Decision(
            call_id=call_id,
            allowed=rule_id is None,
            rule_id=rule_id,
            reason=reason,
            policy_version=version,
            provenance=provenance,
        )

    @staticmethod
    def _decide(
        contract: DomainContract,
        request: CheckRequest,
        record: GuardPolicyRecord | None,
        facts: CallFacts,
    ) -> tuple[str | None, str | None]:
        undeclared = _undeclared(contract, request)
        if undeclared:
            return "contract_undeclared", undeclared
        try:
            rules = rules_of(contract, record)
        except IncompatiblePolicyError as failure:
            return "policy_incompatible", str(failure)
        unresolved = sorted(
            rule.deny_when.argument
            for rule in rules
            if rule.tool == facts.tool
            and isinstance(rule.deny_when, NotOwner)
            and rule.deny_when.argument in facts.arguments
            and rule.deny_when.argument not in facts.owners
        )
        if unresolved:
            return "owner_required", f"El adaptador debe resolver el dueño de {unresolved[0]}."
        denial = first_denial(rules, facts)
        if denial:
            return denial.rule_id, denial.reason
        broken = contract.violations(facts) if contract.enforce_invariants else []
        if broken:
            return f"invariant:{broken[0].id}", broken[0].description
        return None, None
