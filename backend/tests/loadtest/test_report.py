from agent_zero.loadtest.guard_load import GuardSample
from agent_zero.loadtest.participant import AttemptRecord
from agent_zero.loadtest.report import guard_summary, load_summary, mission_summary, percentile


def record(kind: str, attempt_id: str, outcome: str = "apparent_success") -> AttemptRecord:
    done = AttemptRecord("p", kind, "pedido_ajeno" if kind == "attack" else "consulta_propia")
    done.attempt_id, done.submitted, done.admitted, done.finished = attempt_id, 0.0, 1.0, 3.0
    done.status, done.public_outcome = "evaluated", outcome
    return done


def test_percentile_handles_empty_and_bounds() -> None:
    assert percentile([], 0.5) is None
    assert percentile([1.0, 2.0, 3.0], 0.5) == 2.0
    assert percentile([1.0, 2.0, 3.0], 1.0) == 3.0


def test_load_summary_counts_throttling_errors_and_latency() -> None:
    first = record("attack", "a1")
    first.throttled = 2
    broken = AttemptRecord("p", "attack", "memoria", status="timeout")
    broken.errors.append("submit 500")
    summary = load_summary([first, broken], 60.0)
    assert summary["finished"] == 1
    assert summary["timeouts"] == 1
    assert summary["throttled_responses"] == 2
    assert summary["errors"] == {"submit 500": 1}
    assert summary["latency_p50"] == 3.0
    assert summary["run_p50"] == 2.0


def test_mission_summary_splits_by_version_and_measures_the_patch_delay() -> None:
    records = [
        record("honest", "h1", "not_achieved"),
        record("attack", "a1"),
        record("attack", "a2", "not_achieved"),
        record("legit", "l1", "not_achieved"),
    ]
    attempts = [
        {
            "id": "a1",
            "outcome": "confirmed_violation",
            "route": "protected",
            "policy_version": 0,
            "updated_at": "2026-10-24T10:00:00+00:00",
        },
        {
            "id": "a2",
            "outcome": "prevented",
            "route": "protected",
            "policy_version": 1,
            "updated_at": "2026-10-24T10:00:30+00:00",
        },
        {
            "id": "h1",
            "outcome": "not_achieved",
            "route": "protected",
            "policy_version": 0,
            "updated_at": "2026-10-24T10:00:01+00:00",
        },
        {
            "id": "l1",
            "outcome": "not_achieved",
            "route": "protected",
            "policy_version": 1,
            "updated_at": "2026-10-24T10:00:31+00:00",
        },
    ]
    policies = [
        {"version": 0, "status": "superseded", "activated_at": "2026-10-24T09:00:00+00:00"},
        {"version": 1, "status": "active", "activated_at": "2026-10-24T10:00:12+00:00"},
    ]
    summary = mission_summary(records, attempts, policies)
    assert summary["attacks_by_policy_version"] == {
        "0": {"protected:confirmed_violation": 1},
        "1": {"protected:prevented": 1},
    }
    assert summary["legit_false_blocks"] == 0
    assert summary["honest_participant_outcomes"] == {"protected:not_achieved": 1}
    assert summary["participant_apparent_successes"] == 1
    assert summary["seconds_first_violation_to_active_policy"] == 12.0
    assert summary["active_policy_versions"] == [1]


def test_guard_summary_reports_denials_and_allowances() -> None:
    samples = [
        GuardSample("attack", 0.01, 200, False, "r_tope"),
        GuardSample("legit", 0.02, 200, True, None),
        GuardSample("legit", 0.5, 503, None, None),
    ]
    summary = guard_summary(samples, 1.0)
    assert summary["attacks_denied"] == summary["attacks"] == 1
    assert summary["legit_allowed"] == summary["legit"] == 1
    assert summary["non_200"] == 1
    assert summary["deny_rules"] == {"r_tope": 1}
