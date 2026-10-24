from agent_zero.attempts.models import AttemptOutcome
from tests.attempts.conftest import Arena, FakeEvaluator

EMPTY = {
    "accepting": True,
    "policy_version": 0,
    "attempts_total": 0,
    "queued": 0,
    "running": 0,
    "finished": 0,
    "apparent_successes": 0,
    "prevented": 0,
    "not_achieved": 0,
    "inconclusive": 0,
    "findings_open": None,
}


def test_state_starts_empty_and_needs_no_credentials(arena: Arena) -> None:
    response = arena.client.get("/api/arena/state")

    assert response.status_code == 200
    assert response.json() == EMPTY


def test_state_merges_honeypot_and_real_successes_until_reveal(arena: Arena) -> None:
    arena.connect_victim()
    arena.wiring.evaluator = FakeEvaluator(AttemptOutcome.CONTAINED_HONEYPOT)
    auth = arena.session("neo")
    arena.settle(arena.submit(auth, "clave-0001").json()["id"], auth)
    arena.wiring.evaluator = FakeEvaluator(AttemptOutcome.CONFIRMED_VIOLATION)
    other = arena.session("trinity")
    arena.settle(arena.submit(other, "clave-0002").json()["id"], other)
    arena.wiring.policy_version = lambda: 2

    state = arena.client.get("/api/arena/state").json()

    assert state["attempts_total"] == 2
    assert state["finished"] == 2
    assert state["apparent_successes"] == 2
    assert state["policy_version"] == 2
    assert "honeypot" not in str(state)


def test_a_session_lists_only_its_own_attempts_newest_first(arena: Arena) -> None:
    arena.connect_victim()
    mine = arena.session("neo")
    first = arena.submit(mine, "clave-0001", message="primero").json()["id"]
    second = arena.submit(mine, "clave-0002", message="segundo").json()["id"]
    arena.submit(arena.session("trinity"), "clave-0003")

    listed = arena.client.get("/api/attempts", headers=mine).json()

    assert [attempt["id"] for attempt in listed] == [second, first]
    assert all("route" not in attempt for attempt in listed)


def test_listing_needs_a_session(arena: Arena) -> None:
    assert arena.client.get("/api/attempts").status_code == 401
