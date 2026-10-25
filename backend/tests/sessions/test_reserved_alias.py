import pytest
from fastapi.testclient import TestClient

from agent_zero.config import Settings
from agent_zero.sessions.reserved_alias import (
    SWARM_PREFIX,
    TEST_PREFIX,
    is_reserved_alias,
    is_test_alias,
)
from agent_zero.sessions.schemas import SessionCreate
from agent_zero.sessions.session_creation_service import create_session
from agent_zero.shared.database import Database

OPERATOR = {"X-Operator-Secret": "change-me"}


def join(client: TestClient, alias: str, headers: dict[str, str] | None = None) -> int:
    response = client.post(
        "/api/sessions", json={"alias": alias, "accepted_rules": True}, headers=headers or {}
    )
    return response.status_code


@pytest.mark.parametrize("alias", ["Agente-1", "agente-1", "AGENTE-9", " Agente-2"])
def test_the_swarm_prefix_is_rejected_without_the_operator_secret(
    client: TestClient, alias: str
) -> None:
    response = client.post("/api/sessions", json={"alias": alias, "accepted_rules": True})

    assert response.status_code == 409
    assert "reservado" in response.json()["detail"]


def test_the_operator_secret_allows_the_swarm_prefix(client: TestClient) -> None:
    response = client.post(
        "/api/sessions", json={"alias": "Agente-1", "accepted_rules": True}, headers=OPERATOR
    )

    assert response.status_code == 201
    assert response.json()["alias"] == "Agente-1"


@pytest.mark.parametrize("alias", ["Interno-abcd", "interno-x", " INTERNO-1"])
def test_the_test_prefix_is_rejected_without_the_operator_secret(
    client: TestClient, alias: str
) -> None:
    response = client.post("/api/sessions", json={"alias": alias, "accepted_rules": True})

    assert response.status_code == 409
    assert "reservado" in response.json()["detail"]


def test_the_operator_secret_allows_the_test_prefix(client: TestClient) -> None:
    response = client.post(
        "/api/sessions", json={"alias": "Interno-abcd", "accepted_rules": True}, headers=OPERATOR
    )

    assert response.status_code == 201
    assert response.json()["alias"] == "Interno-abcd"


def test_a_wrong_operator_secret_is_unauthorized(client: TestClient) -> None:
    assert join(client, "Agente-1", {"X-Operator-Secret": "otro"}) == 401
    assert join(client, "neo", {"X-Operator-Secret": "otro"}) == 401


@pytest.mark.parametrize("alias", ["Agentes", "Agente 1", "neo-Agente-1", "Internos", "Interno 1"])
def test_aliases_that_only_resemble_the_prefix_stay_open(client: TestClient, alias: str) -> None:
    assert join(client, alias) == 201


def test_the_reservation_covers_every_case_the_board_classifies_as_swarm() -> None:
    assert SWARM_PREFIX == "Agente-"
    for alias in ("Agente-1", "agente-x", "  AGENTE-3"):
        assert is_reserved_alias(alias)
    assert not is_reserved_alias("Agente")


def test_the_reservation_covers_the_test_prefix_without_case_or_padding() -> None:
    assert TEST_PREFIX == "Interno-"
    for alias in ("Interno-abcd", "interno-x", " INTERNO-1"):
        assert is_reserved_alias(alias)
    assert not is_reserved_alias("Internos")
    assert not is_reserved_alias("Interno 1")


@pytest.mark.parametrize(
    ("alias", "expected"),
    [("Interno-abcd", True), ("Internos", False), ("interno-abcd", False), ("neo", False)],
)
def test_only_the_exact_test_prefix_is_a_test_session(alias: str, expected: bool) -> None:
    assert is_test_alias(alias) is expected


async def test_the_service_rejects_the_prefix_unless_the_caller_is_the_operator(
    settings: Settings,
) -> None:
    database = Database(settings.app_database_url)
    await database.create_schema()
    try:
        async with database.sessions() as db:
            with pytest.raises(ValueError, match="reservado"):
                await create_session(db, SessionCreate(alias="Agente-4", accepted_rules=True))
        async with database.sessions() as db:
            created = await create_session(
                db, SessionCreate(alias="Agente-4", accepted_rules=True), operator=True
            )
    finally:
        await database.dispose()
    assert created.alias == "Agente-4"
