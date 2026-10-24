from typing import Any

import pytest
from fastapi.testclient import TestClient

from agent_zero.config import Settings
from agent_zero.guard import contract_registry
from tests.contract.support import CONTRACTS_DIR
from tests.guard.support import GUARD, OPERATOR, SUBJECT, check, effects, guard_client

YUMMY = (CONTRACTS_DIR / "yummy-soporte.yaml").read_text(encoding="utf-8")
TIENDA = YUMMY.replace("contract_id: yummy-soporte", "contract_id: tienda-api", 1)
ATTACK = {
    "subject": SUBJECT,
    "tool": "get_order",
    "arguments": {"order_id": "B-1"},
    "owners": {"order_id": "bruno"},
}


def register(client: TestClient, text: str) -> tuple[int, dict[str, Any]]:
    response = client.post("/api/guard/contracts", content=text, headers=OPERATOR)
    body: dict[str, Any] = response.json()
    return response.status_code, body


def test_registered_contract_guards_and_learns_like_a_file_contract(settings: Settings) -> None:
    with guard_client(settings) as client:
        assert (
            client.post("/api/guard/tienda-api/check", json=ATTACK, headers=GUARD).status_code
            == 404
        )
        status, body = register(client, TIENDA)
        assert status == 201
        assert body["contract"]["source"] == "api"
        first = check(client, "tienda-api", ATTACK)
        assert first["allowed"] is True
        verdict = effects(client, "tienda-api", first["call_id"])
        assert verdict["policy"]["status"] == "active"
        assert check(client, "tienda-api", ATTACK)["allowed"] is False
        assert check(client, "yummy-soporte", ATTACK)["allowed"] is True
        listed = client.get("/api/guard/contracts", headers=OPERATOR).json()
        sources = {row["contract_id"]: row["source"] for row in listed}
        assert sources["tienda-api"] == "api"
        assert sources["yummy-soporte"] == "file"


def test_registered_contract_survives_a_restart(settings: Settings) -> None:
    with guard_client(settings) as client:
        assert register(client, TIENDA)[0] == 201
    with guard_client(settings) as client:
        assert check(client, "tienda-api", ATTACK)["allowed"] is True


def test_replacing_a_contract_keeps_policies_checked_against_the_new_digest(
    settings: Settings,
) -> None:
    with guard_client(settings) as client:
        register(client, TIENDA)
        effects(client, "tienda-api", check(client, "tienda-api", ATTACK)["call_id"])
        renamed = TIENDA.replace("order_id", "pedido")
        status, _ = register(client, renamed)
        assert status == 201
        decision = check(
            client,
            "tienda-api",
            {**ATTACK, "arguments": {"pedido": "B-1"}, "owners": {"pedido": "bruno"}},
        )
        assert decision["allowed"] is False
        assert decision["rule_id"] == "policy_incompatible"


def test_file_contracts_cannot_be_overwritten_and_errors_are_explicit(
    settings: Settings,
) -> None:
    with guard_client(settings) as client:
        assert register(client, YUMMY)[0] == 409
        assert register(client, "contract_id: [")[0] == 422
        assert register(client, TIENDA.replace("kind: resource", "kind: amount", 1))[0] == 422
        anonymous = client.post("/api/guard/contracts", content=TIENDA)
        assert anonymous.status_code == 401


def test_registration_is_capped(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(contract_registry, "MAX_REGISTERED", 1)
    with guard_client(settings) as client:
        assert register(client, TIENDA)[0] == 201
        assert register(client, TIENDA)[0] == 201
        other = TIENDA.replace("contract_id: tienda-api", "contract_id: otra-api", 1)
        assert register(client, other)[0] == 409
