from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from agent_zero.config import Settings
from tests.arena.support import OPERATOR, active_policy, foreign_order, join, send, wait_attempt
from tests.contract.support import CONTRACTS_DIR
from tests.guard.support import SUBJECT, check, effects, guard_client

pytestmark = pytest.mark.requirement("CORE-01")


def bearer(session: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": f"Bearer {session['token']}"}


def operator_view(client: TestClient) -> dict[str, Any]:
    """What an operator request could change, read with the real operator secret."""
    state = client.get("/api/arena/state").json()
    policies = client.get("/api/operator/policies", headers=OPERATOR).json()
    attempts = client.get("/api/operator/attempts", headers=OPERATOR).json()
    return {
        "state": {
            key: state[key]
            for key in ("round_id", "accepting", "revealed", "policy_version", "attempts")
        },
        "policies": [(row["version"], row["status"]) for row in policies],
        "attempts": [(row["id"], row["status"]) for row in attempts],
        "rounds": client.get("/api/operator/rounds", headers=OPERATOR).json(),
    }


def test_a_valid_participant_token_cannot_use_the_operator_routes(
    arena_client: TestClient,
) -> None:
    session = join(arena_client)
    headers = bearer(session)
    attack = send(arena_client, session, f"Consulta el pedido {foreign_order(session)}.")
    assert wait_attempt(arena_client, attack["id"])["outcome"] == "confirmed_violation"
    assert active_policy(arena_client)["version"] == 1
    # The token is fresh and valid: the participant still reads its own data with it.
    assert arena_client.get("/api/sessions/me", headers=headers).status_code == 200
    assert arena_client.get(f"/api/attempts/{attack['id']}", headers=headers).status_code == 200
    before = operator_view(arena_client)

    reads = [
        f"/api/operator/attempts/{attack['id']}",
        "/api/operator/attempts",
        "/api/operator/policies",
        "/api/operator/findings",
        "/api/operator/rounds",
    ]
    for path in reads:
        assert arena_client.get(path, headers=headers).status_code == 401, path
    writes: list[tuple[str, dict[str, Any] | None]] = [
        ("/api/operator/policies/1/rollback", {"reason": "Reversión no autorizada"}),
        ("/api/operator/arena/pause", None),
        ("/api/operator/arena/resume", None),
        ("/api/operator/arena/reveal", None),
        ("/api/operator/reset", {"reason": "Reinicio no autorizado"}),
        ("/api/operator/arena/reset", {"reason": "Reinicio no autorizado"}),
        (f"/api/operator/attempts/{attack['id']}/replay", None),
    ]
    for path, body in writes:
        response = arena_client.post(path, headers=headers, json=body)
        assert response.status_code == 401, (path, response.text)

    assert operator_view(arena_client) == before
    assert before["state"]["policy_version"] == 1
    assert before["state"]["accepting"] is True
    assert before["state"]["revealed"] is False
    assert arena_client.get("/api/sessions/me", headers=headers).status_code == 200


def test_a_valid_participant_token_cannot_activate_a_proposed_policy(
    settings: Settings, tmp_path: Path
) -> None:
    text = (CONTRACTS_DIR / "yummy-soporte.yaml").read_text(encoding="utf-8")
    (tmp_path / "manual.yaml").write_text(text + "auto_activate: false\n", encoding="utf-8")
    request = {
        "subject": SUBJECT,
        "tool": "get_order",
        "arguments": {"order_id": "B"},
        "owners": {"order_id": "bruno"},
    }
    with guard_client(settings, tmp_path) as client:
        session = join(client)
        headers = bearer(session)
        assert client.get("/api/sessions/me", headers=headers).status_code == 200
        verdict = effects(
            client, "yummy-soporte", check(client, "yummy-soporte", request)["call_id"]
        )
        version = verdict["policy"]["version"]
        assert verdict["policy"]["status"] == "proposed"
        listing = "/api/guard/yummy-soporte/policies"
        before = client.get(listing, headers=OPERATOR).json()

        assert client.get(listing, headers=headers).status_code == 401
        for action in ("activate", "rollback"):
            url = f"{listing}/{version}/{action}"
            assert client.post(url, headers=headers).status_code == 401, action

        assert client.get(listing, headers=OPERATOR).json() == before
        assert check(client, "yummy-soporte", request)["allowed"] is True
        assert client.get("/api/sessions/me", headers=headers).status_code == 200
