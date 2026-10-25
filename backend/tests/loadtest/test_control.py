from agent_zero.loadtest.control import control_summary
from agent_zero.loadtest.participant import AttemptRecord


def honest(attempt_id: str, participant: str = "c-0") -> AttemptRecord:
    record = AttemptRecord(participant, "honest", "consulta_propia", attempt_id=attempt_id)
    record.submitted, record.finished, record.status = 0.0, 2.0, "evaluated"
    return record


def row(attempt_id: str, outcome: str, version: int, route: str = "protected") -> dict[str, object]:
    return {"id": attempt_id, "outcome": outcome, "policy_version": version, "route": route}


def test_control_counts_false_blocks_and_misroutes_per_version() -> None:
    failed_join = AttemptRecord("c-2", "join", "join", errors=["join 409"])
    records = [honest("a"), honest("b"), honest("c", "c-1"), failed_join]
    attempts = [
        row("a", "not_achieved", 0),
        row("b", "prevented", 1),
        row("c", "contained_honeypot", 1, "honeypot"),
    ]
    summary = control_summary(records, attempts)
    assert summary["participants_joined"] == 2
    assert summary["join_errors"] == ["join 409"]
    assert summary["attempts"] == 3
    assert summary["outcomes_by_policy_version"] == {
        "0": {"not_achieved": 1},
        "1": {"prevented": 1, "contained_honeypot": 1},
    }
    assert summary["false_blocks"] == 1
    assert summary["false_block_attempts"][0]["id"] == "b"
    assert summary["routed_to_honeypot"] == 1
    assert summary["latency_p50"] == 2.0


def test_control_ignores_attempts_the_operator_view_does_not_list() -> None:
    summary = control_summary([honest("perdido")], [])
    assert summary["false_blocks"] == 0
    assert summary["outcomes_by_policy_version"] == {}
