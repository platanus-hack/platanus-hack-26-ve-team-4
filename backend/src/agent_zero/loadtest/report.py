from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

from agent_zero.loadtest.guard_load import GuardSample
from agent_zero.loadtest.participant import AttemptRecord

PATCH_TARGET_SECONDS = 30.0


def percentile(values: list[float], share: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(share * (len(ordered) - 1))))
    return round(ordered[index], 3)


def _moment(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def load_summary(records: list[AttemptRecord], wall_seconds: float) -> dict[str, Any]:
    finished = [record for record in records if record.finished]
    latencies = [record.latency for record in finished if record.latency is not None]
    runs = [record.run_seconds for record in finished if record.run_seconds is not None]
    errors = Counter(error for record in records for error in record.errors)
    return {
        "attempts": len(records),
        "finished": len(finished),
        "inconclusive": sum(record.status == "inconclusive" for record in records),
        "timeouts": sum(record.status == "timeout" for record in records),
        "throttled_responses": sum(record.throttled for record in records),
        "errors": dict(errors),
        "wall_seconds": round(wall_seconds, 1),
        "throughput_per_minute": round(60 * len(finished) / wall_seconds, 2) if wall_seconds else 0,
        "latency_p50": percentile(latencies, 0.5),
        "latency_p95": percentile(latencies, 0.95),
        "latency_max": percentile(latencies, 1.0),
        "run_p50": percentile(runs, 0.5),
        "run_p95": percentile(runs, 0.95),
    }


def _patch_delay(attempts: list[dict[str, Any]], policies: list[dict[str, Any]]) -> float | None:
    violations = [
        _moment(row.get("updated_at"))
        for row in attempts
        if row.get("outcome") == "confirmed_violation"
    ]
    activations = [_moment(row.get("activated_at")) for row in policies if row.get("version")]
    first_violation = min((moment for moment in violations if moment), default=None)
    first_active = min((moment for moment in activations if moment), default=None)
    if first_violation is None or first_active is None:
        return None
    return round((first_active - first_violation).total_seconds(), 2)


def mission_summary(
    records: list[AttemptRecord],
    attempts: list[dict[str, Any]],
    policies: list[dict[str, Any]],
) -> dict[str, Any]:
    private = {row["id"]: row for row in attempts}
    by_version: dict[int, Counter[str]] = defaultdict(Counter)
    by_family: dict[str, Counter[str]] = defaultdict(Counter)
    by_family_version: dict[str, Counter[str]] = defaultdict(Counter)
    legit: Counter[str] = Counter()
    honest: Counter[str] = Counter()
    apparent = 0
    for record in records:
        row = private.get(record.attempt_id or "")
        if row is None:
            continue
        outcome = str(row.get("outcome"))
        if record.kind == "honest":
            honest[f"{row['route']}:{outcome}"] += 1
            continue
        if record.kind == "legit":
            legit[outcome] += 1
            continue
        by_version[int(row["policy_version"])][f"{row['route']}:{outcome}"] += 1
        by_family[record.family][outcome] += 1
        by_family_version[f"{record.family}@v{row['policy_version']}"][outcome] += 1
        apparent += record.public_outcome == "apparent_success"
    active = [row for row in policies if row.get("version") and row.get("status") == "active"]
    return {
        "attacks_by_policy_version": {
            str(key): dict(value) for key, value in sorted(by_version.items())
        },
        "attacks_by_family": {key: dict(value) for key, value in sorted(by_family.items())},
        "attacks_by_family_and_version": {
            key: dict(value) for key, value in sorted(by_family_version.items())
        },
        "legit_outcomes": dict(legit),
        "legit_false_blocks": legit["prevented"],
        "honest_participant_outcomes": dict(honest),
        "participant_apparent_successes": apparent,
        "policies": [
            {key: row.get(key) for key in ("version", "status", "activated_at")} for row in policies
        ],
        "active_policy_versions": [row["version"] for row in active],
        "seconds_first_violation_to_active_policy": _patch_delay(attempts, policies),
        "patch_target_seconds": PATCH_TARGET_SECONDS,
    }


def guard_summary(samples: list[GuardSample], wall_seconds: float) -> dict[str, Any]:
    latencies = [sample.latency for sample in samples if sample.status == 200]
    attacks = [sample for sample in samples if sample.kind == "attack" and sample.status == 200]
    legit = [sample for sample in samples if sample.kind == "legit" and sample.status == 200]
    return {
        "checks": len(samples),
        "non_200": sum(sample.status != 200 for sample in samples),
        "checks_per_second": round(len(samples) / wall_seconds, 1) if wall_seconds else 0,
        "latency_p50": percentile(latencies, 0.5),
        "latency_p95": percentile(latencies, 0.95),
        "latency_max": percentile(latencies, 1.0),
        "attacks_denied": sum(sample.allowed is False for sample in attacks),
        "attacks": len(attacks),
        "legit_allowed": sum(sample.allowed is True for sample in legit),
        "legit": len(legit),
        "deny_rules": dict(Counter(sample.rule_id for sample in attacks if sample.rule_id)),
    }
