import pytest
from fastapi.testclient import TestClient

from agent_zero.routing.models import Route
from tests.arena.support import join, send, wait_attempt
from tests.arena.test_sticky_honeypot_route import diversion_reasons, stored_route

pytestmark = pytest.mark.requirement("CORE-06")


def typo(order_id: str) -> str:
    return order_id[:-1] + ("9" if order_id[-1] != "9" else "8")


def ask(client: TestClient, session: dict[str, object], text: str, key: str) -> dict[str, object]:
    return wait_attempt(client, send(client, session, text, key)["id"])


def test_an_honest_customer_who_mistypes_stays_protected(arena_client: TestClient) -> None:
    session = join(arena_client, "honesta")
    own = str(session["order_ids"][0])
    for turn in range(4):
        ask(arena_client, session, f"Consulta mi pedido {typo(own)}.", f"typo-{turn}")
    final = ask(arena_client, session, f"Consulta mi pedido {own}.", "real")
    assert final["route"] == "protected", final
    assert stored_route(arena_client, str(session["id"])) == Route.PROTECTED


def test_enumeration_interleaved_with_real_queries_is_diverted(
    arena_client: TestClient,
) -> None:
    session = join(arena_client, "enumera")
    own = str(session["order_ids"][0])
    letter = "B" if own.startswith("A") else "A"
    for number in range(4):
        probe = f"{letter}-990{number}"
        ask(arena_client, session, f"Consulta el pedido {probe}.", f"probe-{number}")
        ask(arena_client, session, f"Consulta mi pedido {own}.", f"legit-{number}")
    final = ask(arena_client, session, f"Consulta mi pedido {own}.", "final")
    assert final["route"] == "honeypot", final
    assert diversion_reasons(arena_client, str(session["id"])) == ["risk_score"]
