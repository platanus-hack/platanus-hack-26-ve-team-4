from agent_zero.attempts.models import AttemptOutcome
from agent_zero.live.models import LiveBoard
from agent_zero.live.service import BoardData, build_board
from tests.live.support import attempt, session

OBJ = "OBJ-ORDER"


def board(revealed: bool = False) -> LiveBoard:
    rows = [
        attempt(
            "a-int",
            "sess-int",
            seconds=10,
            outcome=AttemptOutcome.CONFIRMED_VIOLATION,
            violated=[OBJ],
        ),
        attempt("a-pub", "sess-pub", seconds=20, outcome=AttemptOutcome.NOT_ACHIEVED),
    ]
    sessions = [session("sess-int", "Interno-abcd"), session("sess-pub", "neo")]
    data = BoardData(rows, sessions, [], [], [])
    return build_board(data, revealed=revealed, llm_mode="demo", limit=6)


def test_a_test_session_is_shown_unmasked_before_the_reveal() -> None:
    live = {s.session_id: s for s in board().sessions}

    internal = live["sess-int"]
    assert internal.kind == "test"
    assert internal.concealed is False
    assert internal.route == "protected"
    assert internal.attempts[0].outcome == "confirmed_violation"


def test_test_sessions_do_not_move_the_kpis_or_the_session_count() -> None:
    result = board()

    assert result.kpis.attacks.n == 1
    assert result.kpis.attacks.audience == 1
    assert result.kpis.leaked.leaked == 0
    assert result.sessions_total == 1


def test_automated_test_chats_move_the_kpis_and_stay_unmasked() -> None:
    rows = [
        attempt(
            "a-auto",
            "sess-auto",
            seconds=10,
            outcome=AttemptOutcome.CONFIRMED_VIOLATION,
            violated=[OBJ],
        ),
        attempt("a-int", "sess-int", seconds=20, outcome=AttemptOutcome.NOT_ACHIEVED),
    ]
    sessions = [
        session("sess-auto", "Interno-Auto-N4-2-Ingrid-1"),
        session("sess-int", "Interno-x"),
    ]
    result = build_board(
        BoardData(rows, sessions, [], [], []), revealed=False, llm_mode="live", limit=6
    )

    auto = {s.session_id: s for s in result.sessions}["sess-auto"]
    assert auto.kind == "test"
    assert auto.concealed is False
    assert result.kpis.attacks.n == 1
    assert result.kpis.leaked.leaked == 1
    assert result.sessions_total == 1
