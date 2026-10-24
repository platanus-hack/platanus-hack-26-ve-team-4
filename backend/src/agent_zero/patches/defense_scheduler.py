import json
from typing import Any

from agent_zero.analyzer.finding_service import FindingService
from agent_zero.attempts.attempt_query_service import AttemptQueryService
from agent_zero.fleet.fleet_builder import Fleet
from agent_zero.memory_bank.memory_quarantine_service import quarantine_matching
from agent_zero.policies.memory_rules import changes_permissions
from agent_zero.policies.policy_service import PolicyService
from agent_zero.policies.validator_catalog import ValidatorName
from agent_zero.runtime.run_enqueue_service import RunEnqueueService
from agent_zero.runtime.schemas import RunCreate
from agent_zero.victim.arena_manifest import ARENA_VERSION, PATCH_HANDLER
from agent_zero.victim.environments import Environments


def _permission_memory(content: str) -> bool:
    try:
        data = json.loads(content)
        return changes_permissions(str(data["key"]), str(data["value"]))
    except (ValueError, TypeError, KeyError):
        return True


class DefenseScheduler:
    def __init__(
        self,
        fleet: Fleet,
        policies: PolicyService,
        findings: FindingService,
        attempts: AttemptQueryService,
        environments: Environments,
    ) -> None:
        self._fleet = fleet
        self._policies = policies
        self._findings = findings
        self._attempts = attempts
        self._environments = environments

    async def tick(self) -> None:
        policies = await self._policies.all()
        for policy in policies:
            needs_finalizing = (
                policy["status"] == "active"
                and policy["version"] > 0
                and not policy["validation"].get("finalized")
            )
            if needs_finalizing:
                await self._findings.mitigate(policy["finding_ids"])
                await self._policies.finalize(int(policy["version"]))
        pending = next(
            (row for row in policies if row["status"] in {"candidate", "validating"}), None
        )
        if pending is not None:
            version = int(pending["version"])
            if pending["validation"].get("passed"):

                async def quarantine() -> None:
                    await self._quarantine(pending)

                if await self._policies.activate(
                    version, self._attempts.drained, before_activate=quarantine
                ):
                    await self._findings.mitigate(pending["finding_ids"])
                    await self._policies.finalize(version)
                return
            findings = await self._findings.all()
            finding = next(row for row in findings if row["id"] in pending["finding_ids"])
            async with self._fleet.database.sessions() as db:
                run = await RunEnqueueService(db, self._fleet.handlers).enqueue(
                    RunCreate(
                        agent_id="generador-parches",
                        agent_version=ARENA_VERSION,
                        handler=PATCH_HANDLER,
                        idempotency_key=f"patch:{version}",
                        input={
                            "version": version,
                            "attempt_id": (
                                pending["validation"].get("evidence_attempt_ids")
                                or finding["attempt_ids"]
                            )[-1],
                            "objective_id": finding["objective_id"],
                        },
                    )
                )
            if run.status.terminal and run.failure_reason:
                await self._policies.start_validation(version)
                await self._policies.record_validation(
                    version,
                    {
                        "passed": False,
                        "reason": "Falló el run de validación.",
                    },
                )
            return
        if not self._fleet.settings.arena_auto_patch:
            return
        active = await self._policies.active_version()
        findings = await self._findings.all()
        for finding in findings:
            if finding["status"] not in {"open", "reopened"}:
                continue
            tried = any(
                finding["id"] in row["finding_ids"]
                and row["parent_version"] == active
                and (
                    not row["validation"].get("evidence_attempt_ids")
                    or set(finding["attempt_ids"]) <= set(row["validation"]["evidence_attempt_ids"])
                )
                for row in policies
            )
            if not tried:
                related = [
                    row
                    for row in findings
                    if row["id"] != finding["id"]
                    and finding["attempt_ids"][-1] in row["attempt_ids"]
                ]
                await self._policies.propose(
                    finding["id"],
                    finding["objective_id"],
                    related=[(row["id"], row["objective_id"]) for row in related],
                    evidence_attempt_ids=finding["attempt_ids"],
                )
                break

    async def _quarantine(self, policy: dict[str, Any]) -> None:
        if ValidatorName.MEMORY_KEYS in policy["rules"]:
            for name in ("protected", "honeypot"):
                async with self._environments.get(name).database.sessions() as db:
                    await quarantine_matching(db, self._fleet.cipher, _permission_memory)
