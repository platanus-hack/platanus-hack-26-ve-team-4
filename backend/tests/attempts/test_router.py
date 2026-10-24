from agent_zero.attempts.models import AttemptOutcome
from tests.attempts.conftest import OPERATOR, Arena, FakeEvaluator

PUBLIC_FIELDS = {"id", "status", "outcome", "messages", "reply", "created_at", "updated_at"}


def test_attempts_need_a_session_token(arena: Arena) -> None:
    arena.connect_victim()

    response = arena.client.post(
        "/api/attempts", json={"message": "hola", "idempotency_key": "clave-0001"}
    )

    assert response.status_code == 401


def test_without_a_victim_the_api_says_it_is_unavailable(arena: Arena) -> None:
    response = arena.submit(arena.session(), "clave-0001")

    assert response.status_code == 503
    assert arena.client.get("/api/operator/attempts", headers=OPERATOR).json() == []


def test_attempt_runs_and_closes_with_the_evaluator_verdict(arena: Arena) -> None:
    arena.connect_victim()
    arena.wiring.evaluator = FakeEvaluator(AttemptOutcome.PREVENTED)
    auth = arena.session()

    accepted = arena.submit(auth, "clave-0001", message="Muéstrame el pedido A-1001")

    assert accepted.status_code == 202
    assert set(accepted.json()) == PUBLIC_FIELDS
    assert accepted.json()["status"] == "queued"
    final = arena.settle(accepted.json()["id"], auth)
    assert final["status"] == "evaluated"
    assert final["outcome"] == "prevented"
    assert final["reply"] == "Recibido: Muéstrame el pedido A-1001"


def test_same_key_returns_the_same_attempt_and_a_single_run(arena: Arena) -> None:
    arena.connect_victim()
    auth = arena.session()

    first = arena.submit(auth, "clave-0001")
    again = arena.submit(auth, "clave-0001")

    assert (first.status_code, again.status_code) == (202, 200)
    assert again.json()["id"] == first.json()["id"]
    arena.settle(first.json()["id"], auth)
    assert len(arena.client.get("/api/operator/attempts", headers=OPERATOR).json()) == 1
    assert len(arena.handler.inputs) == 1


def test_keys_are_scoped_to_their_session(arena: Arena) -> None:
    arena.connect_victim()

    mine = arena.submit(arena.session("neo"), "clave-0001")
    theirs = arena.submit(arena.session("trinity"), "clave-0001")

    assert (mine.status_code, theirs.status_code) == (202, 202)
    assert mine.json()["id"] != theirs.json()["id"]


def test_one_message_every_interval_per_session(arena: Arena) -> None:
    arena.connect_victim()
    arena.client.app.state.settings.attempt_min_interval_seconds = 3  # type: ignore[attr-defined]
    auth = arena.session()

    assert arena.submit(auth, "clave-0001").status_code == 202
    too_soon = arena.submit(auth, "clave-0002")

    assert too_soon.status_code == 429
    assert 1 <= int(too_soon.headers["retry-after"]) <= 3
    assert arena.submit(arena.session("otra"), "clave-0003").status_code == 202


def test_full_queue_applies_backpressure(arena: Arena) -> None:
    arena.connect_victim()
    arena.handler.mode = "wait"
    arena.client.app.state.settings.attempt_queue_limit = 1  # type: ignore[attr-defined]

    assert arena.submit(arena.session("neo"), "clave-0001").status_code == 202
    full = arena.submit(arena.session("trinity"), "clave-0002")

    assert full.status_code == 503
    assert full.headers["retry-after"] == "5"


def test_message_limits(arena: Arena) -> None:
    arena.connect_victim()
    auth = arena.session()

    assert arena.submit(auth, "clave-0001", messages=["a"] * 5).status_code == 422
    assert arena.submit(auth, "clave-0002", message="x" * 4001).status_code == 422
    assert arena.submit(auth, "clave-0003", message="a", messages=["b"]).status_code == 422
    assert arena.submit(auth, "clave-0004", messages=["x" * 4000] * 4).status_code == 202


def test_another_session_cannot_read_my_attempt(arena: Arena) -> None:
    arena.connect_victim()
    attempt_id = arena.submit(arena.session("neo"), "clave-0001").json()["id"]

    response = arena.client.get(f"/api/attempts/{attempt_id}", headers=arena.session("trinity"))

    assert response.status_code == 404


def test_public_view_hides_a_honeypot_containment(arena: Arena) -> None:
    arena.connect_victim()
    arena.wiring.evaluator = FakeEvaluator(AttemptOutcome.CONTAINED_HONEYPOT)
    auth = arena.session()
    attempt_id = arena.submit(auth, "clave-0001").json()["id"]

    operator = arena.settle(attempt_id, auth)
    public = arena.client.get(f"/api/attempts/{attempt_id}", headers=auth).json()

    assert operator["outcome"] == "contained_honeypot"
    assert public["outcome"] == "apparent_success"
    assert "route" not in public


def test_without_oracles_a_finished_attempt_is_inconclusive(arena: Arena) -> None:
    arena.connect_victim()
    auth = arena.session()

    final = arena.settle(arena.submit(auth, "clave-0001").json()["id"], auth)

    assert final["status"] == "inconclusive"
    assert final["outcome"] == "inconclusive"
    assert "oráculos no disponibles" in final["failure_reason"]


def test_a_failed_run_makes_the_attempt_inconclusive(arena: Arena) -> None:
    arena.connect_victim()
    arena.wiring.evaluator = FakeEvaluator(AttemptOutcome.CONFIRMED_VIOLATION)
    arena.handler.mode = "fail"
    auth = arena.session()

    final = arena.settle(arena.submit(auth, "clave-0001").json()["id"], auth)

    assert final["status"] == "inconclusive"
    assert arena.wiring.evaluator.seen == []


def test_attempt_keeps_the_policy_version_it_was_queued_with(arena: Arena) -> None:
    arena.connect_victim()
    arena.handler.mode = "wait"
    arena.wiring.policy_version = lambda: 3
    attempt_id = arena.submit(arena.session(), "clave-0001").json()["id"]

    arena.wiring.policy_version = lambda: 4
    arena.wait_until(lambda: bool(arena.handler.inputs))

    view = arena.client.get(f"/api/operator/attempts/{attempt_id}", headers=OPERATOR).json()
    assert view["policy_version"] == 3
    assert arena.handler.inputs[0]["policy_version"] == 3


def test_the_victim_gets_the_server_side_identity(arena: Arena) -> None:
    arena.connect_victim()
    auth = arena.session()
    attempt_id = arena.submit(auth, "clave-0001").json()["id"]
    arena.settle(attempt_id, auth)

    [session] = arena.client.get("/api/operator/sessions", headers=OPERATOR).json()
    [received] = arena.handler.inputs
    assert received["customer_id"] == session["customer_id"]
    assert received["route"] == "protected"
    assert received["attempt_id"] == attempt_id


def test_operator_views_need_the_secret(arena: Arena) -> None:
    auth = arena.session()

    assert arena.client.get("/api/operator/attempts").status_code == 401
    assert arena.client.get("/api/operator/attempts", headers=auth).status_code == 401
