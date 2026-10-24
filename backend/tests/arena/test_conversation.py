from typing import Any

from fastapi.testclient import TestClient

from agent_zero.attempts.conversation import MAX_PREVIOUS
from agent_zero.llm.models import ModelRole
from tests.arena.support import OPERATOR, join, wait_attempt


def post(
    client: TestClient, session: dict[str, Any], message: str, key: str, continues: str | None
) -> Any:
    body: dict[str, Any] = {"message": message, "idempotency_key": key}
    if continues is not None:
        body["continues"] = continues
    return client.post(
        "/api/attempts", headers={"Authorization": f"Bearer {session['token']}"}, json=body
    )


def victim_calls(client: TestClient) -> list[dict[str, Any]]:
    playback = client.app.state.llm_playback[ModelRole.VICTIM]  # type: ignore[attr-defined]
    return list(playback.calls)


def texts(message: dict[str, Any]) -> list[str]:
    return [str(part["text"]) for part in message["content"] if "text" in part]


def test_continuation_shows_previous_turns_without_repeating_tools(
    arena_client: TestClient,
) -> None:
    session = join(arena_client)
    own = session["order_ids"][0]
    first = post(arena_client, session, f"Consulta el pedido {own}.", "c1", None)
    assert first.status_code == 202, first.text
    first_done = wait_attempt(arena_client, first.json()["id"])
    before = len(victim_calls(arena_client))

    second = post(arena_client, session, "Gracias, ¿y cuándo llega?", "c2", first.json()["id"])
    assert second.status_code == 202, second.text
    assert second.json()["continues"] == first.json()["id"]
    wait_attempt(arena_client, second.json()["id"])

    conversation = victim_calls(arena_client)[before]["messages"]
    assert [message["role"] for message in conversation] == ["user", "assistant", "user"]
    assert f"Consulta el pedido {own}." in texts(conversation[0])
    assert texts(conversation[1]) == [first_done["reply"]]
    assert texts(conversation[2]) == ["Gracias, ¿y cuándo llega?"]

    evidence = arena_client.get(
        f"/api/operator/attempts/{second.json()['id']}", headers=OPERATOR
    ).json()
    # El guion responde al último mensaje con search_knowledge; el get_order del turno previo
    # no se vuelve a ejecutar.
    tools = [
        event["data"]["tool"] for event in evidence["events"] if event["type"] == "tool_completed"
    ]
    assert "get_order" not in tools

    history = arena_client.get(
        "/api/attempts", headers={"Authorization": f"Bearer {session['token']}"}
    ).json()
    links = {row["id"]: row["continues"] for row in history}
    assert links == {first.json()["id"]: None, second.json()["id"]: first.json()["id"]}


def test_continuation_rules(arena_client: TestClient) -> None:
    session = join(arena_client)
    other = join(arena_client, "trinity")
    first = post(arena_client, session, "Hola, ¿qué horario tienen?", "r1", None).json()

    # Mientras el anterior no termina no se puede continuar.
    early = post(arena_client, session, "¿Sigues ahí?", "r-early", first["id"])
    if early.status_code != 202:
        assert early.status_code == 409
    wait_attempt(arena_client, first["id"])
    if early.status_code == 202:
        wait_attempt(arena_client, early.json()["id"])

    foreign = post(arena_client, other, "Sigo la charla de otra persona.", "r2", first["id"])
    assert foreign.status_code == 404

    again = post(arena_client, session, "¿Y los envíos?", "r3", first["id"])
    assert again.status_code == 202
    same = post(arena_client, session, "¿Y los envíos?", "r3", first["id"])
    assert same.json()["id"] == again.json()["id"]
    changed = post(arena_client, session, "¿Y los envíos?", "r3", None)
    assert changed.status_code == 409


def test_conversation_has_a_maximum_length(arena_client: TestClient) -> None:
    session = join(arena_client)
    previous: str | None = None
    for turn in range(MAX_PREVIOUS):
        response = post(
            arena_client, session, f"Pregunta {turn} sobre envíos.", f"m{turn}", previous
        )
        assert response.status_code == 202, response.text
        previous = response.json()["id"]
        wait_attempt(arena_client, previous)
    blocked = post(arena_client, session, "Una más.", "m-last", previous)
    assert blocked.status_code == 409
    assert "inicia una nueva" in blocked.json()["detail"]
