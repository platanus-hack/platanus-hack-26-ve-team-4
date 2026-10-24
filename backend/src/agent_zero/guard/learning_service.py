import uuid
from dataclasses import replace
from typing import Any

from agent_zero.arena.transactions import serialize_write
from agent_zero.contract.conditions import CallFacts
from agent_zero.contract.schema import DomainContract, Invariant
from agent_zero.guard.derivation import merge
from agent_zero.guard.enforcement import gate
from agent_zero.guard.facts import dump, load
from agent_zero.guard.models import GuardCallRecord, GuardFindingRecord, GuardPolicyRecord
from agent_zero.guard.repository import active_policy, next_version, rules_of
from agent_zero.guard.schemas import EffectReport, EffectVerdict
from agent_zero.guard.synthesizer import GuardSynthesizer
from agent_zero.guard.views import policy_view
from agent_zero.shared.database import Database


class UnknownCallError(LookupError):
    pass


class GuardLearningService:
    def __init__(self, database: Database, synthesizer: GuardSynthesizer) -> None:
        self._database, self._synthesizer = database, synthesizer

    async def report(self, contract: DomainContract, report: EffectReport) -> EffectVerdict:
        async with self._database.sessions() as db:
            await serialize_write(db)
            call = await db.get(GuardCallRecord, report.call_id)
            if call is None or call.contract_id != contract.contract_id or not call.allowed:
                raise UnknownCallError(report.call_id)
            if call.effect is not None:
                return EffectVerdict.model_validate({"call_id": call.call_id, **call.effect})
            stored = load(call.facts)
            facts = CallFacts(
                stored.tool,
                report.arguments if report.arguments is not None else stored.arguments,
                stored.subject,
                stored.provenance,
                {**stored.owners, **report.owners},
                stored.totals,
            )
            violated = contract.violations(facts)
            finding_id = f"gf-{uuid.uuid4().hex[:20]}" if violated else None
            call.facts = dump(facts)
            call.effect = {"violations": [item.id for item in violated], "finding_id": finding_id}
            if finding_id:
                db.add(
                    GuardFindingRecord(
                        id=finding_id,
                        contract_id=contract.contract_id,
                        call_id=call.call_id,
                        invariant_ids=[item.id for item in violated],
                        policy_version=call.policy_version,
                    )
                )
            await db.commit()
        if finding_id is None:
            return EffectVerdict(call_id=report.call_id, violations=[])
        policy = await self._learn(contract, finding_id, violated, facts)
        verdict = EffectVerdict(
            call_id=report.call_id,
            violations=[item.id for item in violated],
            finding_id=finding_id,
            policy=policy,
        )
        await self._store_verdict(report.call_id, verdict)
        return verdict

    async def learn_from_blocked(
        self, contract: DomainContract, call_id: str, facts: CallFacts, version: int
    ) -> dict[str, Any]:
        async with self._database.sessions() as db:
            call = await db.get(GuardCallRecord, call_id)
        if call is not None:
            facts = replace(facts, totals=load(call.facts).totals)
        violated = contract.violations(facts)
        finding_id = f"gf-{uuid.uuid4().hex[:20]}"
        async with self._database.sessions() as db, db.begin():
            db.add(
                GuardFindingRecord(
                    id=finding_id,
                    contract_id=contract.contract_id,
                    call_id=call_id,
                    invariant_ids=[item.id for item in violated],
                    policy_version=version,
                )
            )
        return await self._learn(contract, finding_id, violated, facts)

    async def _learn(
        self,
        contract: DomainContract,
        finding_id: str,
        violated: list[Invariant],
        facts: CallFacts,
    ) -> dict[str, Any]:
        async with self._database.sessions() as db:
            inherited = rules_of(contract, await active_policy(db, contract.contract_id))
        rules, report = await self._synthesizer.propose(contract, inherited, violated, facts)
        async with self._database.sessions() as db:
            await serialize_write(db)
            parent = await active_policy(db, contract.contract_id)
            rules = merge(rules_of(contract, parent), rules)
            report["gate"] = gate(contract, rules, [facts])
            accepted = bool(report["gate"]["accepted"])
            status = "rejected"
            if accepted:
                status = "active" if contract.auto_activate else "proposed"
            if status == "active" and parent is not None:
                parent.status = "superseded"
            record = GuardPolicyRecord(
                contract_id=contract.contract_id,
                version=await next_version(db, contract.contract_id),
                parent_version=parent.version if parent else 0,
                status=status,
                rules=[rule.model_dump(mode="json") for rule in rules],
                report=report,
                finding_id=finding_id,
                contract_digest=contract.digest(),
            )
            db.add(record)
            await db.flush()
            finding = await db.get(GuardFindingRecord, finding_id)
            if finding is not None and accepted:
                finding.resolved_by = record.version
            view = policy_view(record)
            await db.commit()
        return view

    async def _store_verdict(self, call_id: str, verdict: EffectVerdict) -> None:
        async with self._database.sessions() as db, db.begin():
            call = await db.get(GuardCallRecord, call_id)
            if call is not None:
                call.effect = verdict.model_dump(mode="json", exclude={"call_id"})
