from typing import Any

from agent_zero.attempts.models import Attempt, AttemptOutcome, AttemptStatus
from agent_zero.live.models import LiveBoard, LiveDenial, LiveTechnique
from agent_zero.live.service import BoardData, build_board
from agent_zero.llm.models import CallOrigin
from agent_zero.llm.schemas import CallRecord
from agent_zero.routing.models import Route
from agent_zero.sessions.models import ArenaSession
from tests.live.support import at, attempt, call, session

OBJ = "OBJ-ORDER"
SECRET_REPLY = "Respuesta del Público con datos ajenos."


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
            reply=SECRET_REPLY,
        ),
        attempt(
            "a2",
            "sess-pub",
            seconds=20,
            outcome=AttemptOutcome.CONTAINED_HONEYPOT,
            route=Route.HONEYPOT,
            reply=SECRET_REPLY,
        ),
        attempt(
            "a3",
            "sess-sw",
            seconds=30,
            outcome=AttemptOutcome.CONFIRMED_VIOLATION,
            violated=[OBJ],
        ),
        attempt("a4", "internal-pr", seconds=40, campaign_id="camp-0001"),
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
    rows: list[Attempt] | None = None,
    extra: list[ArenaSession] | None = None,
    accepting: bool = True,
    denials: dict[str, list[LiveDenial]] | None = None,
    techniques: dict[str, LiveTechnique] | None = None,
) -> LiveBoard:
    data = BoardData(
        rows if rows is not None else attempts(),
        sessions() + (extra or []),
        policies or [],
        findings or [],
        records or [],
        denials or {},
        techniques or {},
    )
    return build_board(data, revealed=revealed, llm_mode=mode, limit=limit, accepting=accepting)


def test_sessions_are_classified_ordered_by_activity_and_exclude_replays() -> None:
    result = board(revealed=True)

    assert [(s.session_id, s.kind) for s in result.sessions] == [
        ("camp-0001", "prober"),
        ("sess-sw", "swarm"),
        ("sess-pub", "audience"),
    ]
    assert [a.id for a in result.sessions[2].attempts] == ["a1", "a2"]
    assert [a.number for a in result.sessions[2].attempts] == [1, 2]
    assert result.sessions_total == 3
    assert result.kpis.attacks.n == 4
    assert (result.kpis.attacks.audience, result.kpis.attacks.swarm) == (2, 1)
    assert result.kpis.attacks.prober == 1


def test_limit_keeps_the_most_recent_sessions() -> None:
    limited = board(revealed=True, limit=1)

    assert [s.session_id for s in limited.sessions] == ["camp-0001"]
    assert limited.sessions_total == 3


def test_the_audience_travels_without_outcome_route_or_reply_until_the_reveal() -> None:
    hidden = board(
        revealed=False,
        denials={"a1": [LiveDenial(tool="get_order", reason="rate_limited", validator=None)]},
    )
    audience = {s.kind: s for s in hidden.sessions}["audience"]

    assert audience.concealed is True
    assert audience.route is None
    assert (audience.contained_n, audience.prevented_n, audience.leaked_n) == (None, None, None)
    for item in audience.attempts:
        assert (item.outcome, item.route, item.reply) == (None, None, "")
        assert (item.denials, item.violated_objectives) == ([], [])
        assert (item.patched_by, item.technique) == (None, None)
        assert item.messages == ["Mensaje."]
    assert SECRET_REPLY not in hidden.model_dump_json()
    assert "rate_limited" not in hidden.model_dump_json()

    swarm = {s.kind: s for s in hidden.sessions}["swarm"]
    assert swarm.concealed is False
    assert swarm.route == "protected"
    assert swarm.attempts[0].outcome == "confirmed_violation"
    assert swarm.attempts[0].violated_objectives == [OBJ]
    assert swarm.leaked_n == 1


def test_after_the_reveal_the_audience_shows_route_and_real_outcome() -> None:
    audience = {s.kind: s for s in board(revealed=True).sessions}["audience"]

    assert audience.concealed is False
    assert audience.route == "honeypot"
    assert [a.outcome for a in audience.attempts] == ["confirmed_violation", "contained_honeypot"]
    assert audience.attempts[1].route == "honeypot"
    assert audience.attempts[0].reply == SECRET_REPLY
    assert (audience.contained_n, audience.leaked_n) == (1, 1)


def test_denials_and_techniques_are_attached_to_their_attempts() -> None:
    denial = LiveDenial(
        tool="get_order", reason="business_rule_denied", validator="order_belongs_to_session"
    )
    technique = LiveTechnique(family="tool_misuse", mutator="paraphrase_es")
    result = board(revealed=True, denials={"a3": [denial]}, techniques={"a4": technique})
    by_kind = {s.kind: s for s in result.sessions}

    assert by_kind["swarm"].attempts[0].denials == [denial]
    assert by_kind["swarm"].attempts[0].technique is None
    assert by_kind["prober"].attempts[0].technique == technique


def test_kpis_two_and_three_count_only_swarm_and_prober_before_the_reveal() -> None:
    hidden = board(revealed=False).kpis
    assert hidden.leaked.scope == "swarm_prober"
    assert (hidden.leaked.leaked, hidden.leaked.n) == (1, 2)
    assert hidden.leaked.by_objective == {"OBJ-ORDER": 1, "OBJ-REFUND": 0, "OBJ-MEMORY": 0}
    assert hidden.leaked.objective_sum == 1
    assert (hidden.safe_space.safe_sessions, hidden.safe_space.n) == (0, 2)
    assert hidden.safe_space.diverted_sessions == 0
    assert hidden.safe_space.contained_attempts == 0
    assert "revelar" in hidden.leaked.label

    shown = board(revealed=True).kpis
    assert shown.leaked.scope == "all"
    assert (shown.leaked.leaked, shown.leaked.n) == (2, 4)
    assert shown.leaked.by_objective["OBJ-ORDER"] == 2
    assert (shown.safe_space.safe_sessions, shown.safe_space.n) == (1, 3)
    assert shown.safe_space.diverted_sessions == 1
    assert shown.safe_space.contained_attempts == 1


def test_only_finished_attempts_count_and_the_rest_are_in_flight() -> None:
    rows = [
        *attempts(),
        attempt("a6", "sess-sw", seconds=60, outcome=None, status=AttemptStatus.RUNNING),
        attempt("a7", "sess-sw", seconds=61, outcome=None, status=AttemptStatus.QUEUED),
    ]
    kpis = board(revealed=False, rows=rows).kpis

    assert (kpis.attacks.n, kpis.attacks.in_flight) == (4, 2)
    assert kpis.leaked.n == 2


def test_a_session_without_attempts_is_not_a_board_session() -> None:
    empty = session("sess-vacia", "trinity", Route.HONEYPOT)
    result = board(revealed=True, extra=[empty])

    assert result.sessions_total == 3
    assert result.kpis.safe_space.n == 3


def test_the_prober_is_grouped_by_campaign_without_losing_the_internal_sessions() -> None:
    extra = [session("internal-p2", "Prober", Route.HONEYPOT), session("internal-p3", "Prober")]
    rows = [
        *attempts(),
        attempt("b1", "internal-p2", seconds=60, campaign_id="camp-0001", route=Route.HONEYPOT),
        attempt("b2", "internal-p3", seconds=70, campaign_id="camp-9abc"),
    ]
    records = [
        call("prober", tokens=100, campaign_id="camp-0001"),
        call("prober", tokens=20, campaign_id="camp-9abc"),
        call("decoy", tokens=7, session_id="internal-p2"),
    ]
    result = board(revealed=True, rows=rows, extra=extra, records=records, mode="live")
    probers = [s for s in result.sessions if s.kind == "prober"]

    assert [(s.session_id, s.alias) for s in probers] == [
        ("camp-9abc", "Prober · 9abc"),
        ("camp-0001", "Prober · 0001"),
    ]
    first = probers[1]
    assert first.attempt_total == 2
    assert [a.number for a in first.attempts] == [1, 2]
    assert first.route == "honeypot"
    assert result.sessions_total == 4
    tokens = result.kpis.attacker_tokens
    assert (tokens.attacker.tokens, tokens.attacker.calls) == (120, 2)
    assert (tokens.decoy.tokens, tokens.decoy.calls) == (7, 1)


def test_only_the_last_thirty_attempts_travel_but_counters_use_all() -> None:
    rows = [
        attempt(
            f"x{index:02d}",
            "sess-sw",
            seconds=index,
            outcome=AttemptOutcome.PREVENTED if index < 5 else AttemptOutcome.NOT_ACHIEVED,
        )
        for index in range(35)
    ]
    swarm = board(revealed=True, rows=rows).sessions[0]

    assert swarm.attempt_total == 35
    assert len(swarm.attempts) == 30
    assert swarm.attempts[0].number == 6
    assert swarm.prevented_n == 5


def test_accepting_reflects_the_arena_state() -> None:
    assert board(revealed=False).accepting is True
    assert board(revealed=False, accepting=False).accepting is False


def test_tokens_are_not_measured_in_demo_instead_of_showing_zero() -> None:
    simulated = [
        call("prober", tokens=100, origin=CallOrigin.SIMULATED, campaign_id="camp-0001"),
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
        call("prober", tokens=300, campaign_id="camp-0001"),
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


def policy(
    version: int, status: str, finding_ids: list[str], activated: float | None
) -> dict[str, Any]:
    return {
        "version": version,
        "status": status,
        "finding_ids": finding_ids,
        "activated_at": None if activated is None else at(activated).isoformat(),
    }


def finding(finding_id: str, created: float, attempt_ids: list[str]) -> dict[str, Any]:
    return {"id": finding_id, "created_at": at(created).isoformat(), "attempt_ids": attempt_ids}


def test_patch_time_is_the_median_from_finding_to_activation_with_fixed_marks() -> None:
    findings = [finding("f1", 0, ["a3"]), finding("f2", 10, ["a4"]), finding("f3", 0, ["a3"])]
    policies = [
        policy(0, "superseded", [], 0),
        policy(1, "superseded", ["f1", "f2"], 20),
        policy(2, "active", ["f3", "f1"], 100),
        policy(3, "rejected", ["f3"], None),
    ]
    patches = board(revealed=True, policies=policies, findings=findings).kpis.patches

    assert (patches.activated, patches.n, patches.current_version) == (2, 2, 2)
    assert patches.median_seconds_to_patch == 20.0  # 20, 10 y 100 segundos.
    assert patches.findings_covered == 3  # f1 cuenta una vez aunque la cubran dos versiones.
    assert patches.findings_covered <= patches.findings_total == 3


def test_rolled_back_policies_and_hidden_audience_findings_do_not_count() -> None:
    findings = [finding("f1", 0, ["a1"]), finding("f2", 0, ["a3"])]
    policies = [policy(1, "rolled_back", ["f2"], 5), policy(2, "active", ["f1"], 9)]

    hidden = board(revealed=False, policies=policies, findings=findings).kpis.patches
    assert (hidden.findings_total, hidden.findings_covered, hidden.activated) == (1, 0, 0)
    assert hidden.median_seconds_to_patch is None

    shown = board(revealed=True, policies=policies, findings=findings).kpis.patches
    assert (shown.findings_total, shown.findings_covered, shown.activated) == (2, 1, 1)


def test_patched_by_needs_a_newer_version_activated_after_the_violation() -> None:
    rows = [
        attempt("v1", "sess-sw", seconds=10, outcome=AttemptOutcome.CONFIRMED_VIOLATION),
        # El hallazgo se reabre: un intento posterior al parche vuelve a violar.
        attempt("v2", "sess-sw", seconds=60, outcome=AttemptOutcome.CONFIRMED_VIOLATION),
        attempt("v3", "sess-sw", seconds=70, outcome=AttemptOutcome.PREVENTED),
    ]
    findings = [finding("f1", 12, ["v1", "v2", "v3"])]
    policies = [
        policy(1, "rolled_back", ["f1"], 14),
        policy(2, "superseded", ["f1"], 25),
        policy(3, "active", ["f1"], 40),
    ]
    by_id = {
        a.id: a
        for a in board(revealed=True, rows=rows, policies=policies, findings=findings)
        .sessions[0]
        .attempts
    }

    first = by_id["v1"].patched_by
    assert first is not None
    assert (first.version, first.seconds_after) == (2, 15.0)
    assert by_id["v2"].patched_by is None
    assert by_id["v3"].patched_by is None


def test_patches_without_findings_report_no_median() -> None:
    patches = board(revealed=True).kpis.patches

    assert patches.median_seconds_to_patch is None
    assert patches.activated == 0
    assert patches.findings_total == 0


def test_running_attempts_keep_their_status_for_the_typing_indicator() -> None:
    pending = attempt("a9", "sess-sw", seconds=60, outcome=None, status=AttemptStatus.RUNNING)

    result = board(revealed=False, rows=[pending])

    assert result.sessions[0].attempts[0].status == "running"
    assert result.sessions[0].attempts[0].outcome is None
    assert result.kpis.attacks.in_flight == 1
