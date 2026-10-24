from typing import Any

from agent_zero.attempts.models import Attempt, AttemptOutcome, AttemptStatus
from agent_zero.live.models import LiveBoard
from agent_zero.live.service import BoardData, build_board
from agent_zero.llm.models import CallOrigin
from agent_zero.llm.schemas import CallRecord
from agent_zero.routing.models import Route
from agent_zero.sessions.models import ArenaSession
from tests.live.support import at, attempt, call, session

OBJ = "OBJ-ORDER"


def sessions() -> list[ArenaSession]:
    return [
        session("sess-pub", "neo", Route.HONEYPOT),
        session("sess-sw", "Agente-1"),
        session("internal-pr", "Prober"),
        session("internal-rp", "Repetición"),
    ]


def attempts() -> list[Attempt]:
    return [
        attempt(
            "a1",
            "sess-pub",
            seconds=10,
            outcome=AttemptOutcome.CONFIRMED_VIOLATION,
            violated=[OBJ],
        ),
        attempt(
            "a2",
            "sess-pub",
            seconds=20,
            outcome=AttemptOutcome.CONTAINED_HONEYPOT,
            route=Route.HONEYPOT,
        ),
        attempt(
            "a3",
            "sess-sw",
            seconds=30,
            outcome=AttemptOutcome.CONFIRMED_VIOLATION,
            violated=[OBJ],
        ),
        attempt("a4", "internal-pr", seconds=40, campaign_id="camp-1"),
        attempt("a5", "internal-rp", seconds=50),
    ]


def board(  # noqa: PLR0913
    *,
    revealed: bool,
    records: list[CallRecord] | None = None,
    policies: list[dict[str, Any]] | None = None,
    findings: list[dict[str, Any]] | None = None,
    limit: int = 6,
    mode: str = "demo",
) -> LiveBoard:
    data = BoardData(attempts(), sessions(), policies or [], findings or [], records or [])
    return build_board(
        data,
        revealed=revealed,
        llm_mode=mode,
        limit=limit,
    )


def test_sessions_are_classified_ordered_by_activity_and_exclude_replays() -> None:
    result = board(revealed=True)

    assert [(s.session_id, s.kind) for s in result.sessions] == [
        ("internal-pr", "prober"),
        ("sess-sw", "swarm"),
        ("sess-pub", "audience"),
    ]
    assert [a.id for a in result.sessions[2].attempts] == ["a1", "a2"]
    assert result.kpis.attacks.n == 4
    assert (result.kpis.attacks.audience, result.kpis.attacks.swarm) == (2, 1)
    assert result.kpis.attacks.prober == 1


def test_limit_keeps_the_most_recent_sessions() -> None:
    assert [s.session_id for s in board(revealed=True, limit=1).sessions] == ["internal-pr"]


def test_audience_is_masked_until_the_reveal() -> None:
    hidden = {s.kind: s for s in board(revealed=False).sessions}

    audience = hidden["audience"]
    assert audience.route is None
    assert all(a.route is None for a in audience.attempts)
    assert [a.outcome for a in audience.attempts] == ["apparent_success", "apparent_success"]
    assert hidden["swarm"].route == "protected"
    assert hidden["swarm"].attempts[0].outcome == "confirmed_violation"
    assert hidden["swarm"].attempts[0].route == "protected"


def test_after_the_reveal_the_audience_shows_route_and_real_outcome() -> None:
    audience = {s.kind: s for s in board(revealed=True).sessions}["audience"]

    assert audience.route == "honeypot"
    assert [a.outcome for a in audience.attempts] == ["confirmed_violation", "contained_honeypot"]
    assert audience.attempts[1].route == "honeypot"


def test_kpis_two_and_three_count_only_swarm_and_prober_before_the_reveal() -> None:
    hidden = board(revealed=False).kpis
    assert hidden.leaked.scope == "swarm_prober"
    assert (hidden.leaked.leaked, hidden.leaked.n) == (1, 2)
    assert hidden.leaked.by_objective == {OBJ: 1}
    assert (hidden.safe_space.diverted_sessions, hidden.safe_space.n) == (0, 2)
    assert hidden.safe_space.contained_attempts == 0
    assert "revelar" in hidden.leaked.label

    shown = board(revealed=True).kpis
    assert shown.leaked.scope == "all"
    assert (shown.leaked.leaked, shown.leaked.n) == (2, 4)
    assert shown.leaked.by_objective == {OBJ: 2}
    assert (shown.safe_space.diverted_sessions, shown.safe_space.n) == (1, 3)
    assert shown.safe_space.contained_attempts == 1


def test_tokens_are_not_measured_in_demo_instead_of_showing_zero() -> None:
    simulated = [
        call("prober", tokens=100, origin=CallOrigin.SIMULATED, campaign_id="camp-1"),
        call("decoy", tokens=None, session_id="sess-sw"),
    ]
    tokens = board(revealed=True, records=simulated).kpis.attacker_tokens

    assert tokens.measured is False
    assert tokens.label == "no medido en modo demo"
    assert tokens.attacker.tokens is None
    assert tokens.decoy.tokens is None
    assert tokens.n == 0
    other = board(revealed=True, mode="live").kpis.attacker_tokens
    assert other.measured is False
    assert other.label == "sin uso de tokens registrado"


def test_tokens_are_summed_from_a_fake_ledger_by_campaign_and_visible_session() -> None:
    records = [
        call("prober", tokens=300, campaign_id="camp-1"),
        call("prober", tokens=50, campaign_id="camp-viejo"),
        call("decoy", tokens=40, session_id="sess-sw"),
        call("decoy", tokens=9, session_id="sess-pub"),
        call("victim", tokens=999, session_id="sess-sw"),
    ]
    hidden = board(revealed=False, records=records, mode="live").kpis.attacker_tokens
    shown = board(revealed=True, records=records, mode="live").kpis.attacker_tokens

    assert hidden.measured is True
    assert hidden.label == ""
    assert (hidden.attacker.tokens, hidden.attacker.calls) == (300, 1)
    assert (hidden.decoy.tokens, hidden.decoy.calls) == (40, 1)
    assert (shown.decoy.tokens, shown.n) == (49, 3)


def test_patch_time_is_the_median_from_finding_to_activation_with_fixed_marks() -> None:
    findings = [
        {"id": "f1", "created_at": at(0).isoformat()},
        {"id": "f2", "created_at": at(10).isoformat()},
        {"id": "f3", "created_at": at(0).isoformat()},
    ]
    policies = [
        {
            "version": 0,
            "status": "superseded",
            "finding_ids": [],
            "activated_at": at(0).isoformat(),
        },
        {
            "version": 1,
            "status": "superseded",
            "finding_ids": ["f1", "f2"],
            "activated_at": at(20).isoformat(),
        },
        {
            "version": 2,
            "status": "active",
            "finding_ids": ["f3"],
            "activated_at": at(100).isoformat(),
        },
        {"version": 3, "status": "rejected", "finding_ids": ["f3"], "activated_at": None},
    ]
    patches = board(revealed=True, policies=policies, findings=findings).kpis.patches

    assert (patches.activated, patches.n, patches.current_version) == (2, 2, 2)
    assert patches.median_seconds_to_patch == 20.0  # 20, 10 y 100 segundos.
    assert patches.findings_covered == 3


def test_patches_without_findings_report_no_median() -> None:
    patches = board(revealed=True).kpis.patches

    assert patches.median_seconds_to_patch is None
    assert patches.activated == 0


def test_running_attempts_keep_their_status_for_the_typing_indicator() -> None:
    pending = attempt("a9", "sess-sw", seconds=60, outcome=None, status=AttemptStatus.RUNNING)

    data = BoardData([pending], sessions(), [], [], [])
    result = build_board(data, revealed=False, llm_mode="demo", limit=6)

    assert result.sessions[0].attempts[0].status == "running"
    assert result.sessions[0].attempts[0].outcome is None
