import json
from typing import Any, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent_zero.agent_gateway.business_policy import CallContext
from agent_zero.arena.core import ProductCore
from agent_zero.victim.arena_manifest import ARENA_VERSION
from agent_zero.victim.controlled_fixtures import ControlledFixture
from tests.victim.knowledge_support import POSTGRES_URL, needs_postgres


class StubIndex:
    ready = True

    def __init__(self) -> None:
        self.text = "Primera versión del fragmento."

    async def search(self, query: str, collections: tuple[str, ...]) -> list[dict[str, str]]:
        return [{"text": self.text, "source": "knowledge:envios", "trust": "lab"}]


def _context(environment: str, operation_id: str) -> CallContext:
    return CallContext(
        attempt_id="attempt-knowledge",
        session_id=f"internal-knowledge-{environment}",
        session_customer_id="cust-ana",
        environment=environment,
        policy_version=0,
        run_id="run-knowledge",
        operation_id=operation_id,
    )


def _core(client: TestClient) -> ProductCore:
    return cast(ProductCore, cast(FastAPI, client.app).state.core)


async def _search(core: ProductCore, context: CallContext, query: str) -> str:
    await core.ensure_agents()
    principal = await core.fleet.admission.admit("soporte-tienda", ARENA_VERSION)
    output = await core.scenario.call("search_knowledge", {"query": query}, context, principal)
    return output.text


@pytest.mark.requirement("CORE-08")
def test_a_repeated_operation_returns_the_saved_result_even_if_the_corpus_changed(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    core = _core(client)
    stub = StubIndex()
    monkeypatch.setattr(core.scenario, "_knowledge", stub)
    context = _context("protected", "knowledge-op-1")
    assert client.portal is not None

    first = client.portal.call(_search, core, context, "¿Cuánto tarda el envío?")
    stub.text = "Segunda versión del fragmento."
    again = client.portal.call(_search, core, context, "¿Cuánto tarda el envío?")
    other = client.portal.call(
        _search, core, _context("protected", "knowledge-op-2"), "¿Cuánto tarda el envío?"
    )

    assert again == first
    assert json.loads(first)["articles"][0]["text"] == "Primera versión del fragmento."
    assert json.loads(other)["articles"][0]["text"] == "Segunda versión del fragmento."


@pytest.mark.requirement("CORE-08")
def test_documents_of_a_controlled_fixture_still_arrive_untrusted(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    core = _core(client)
    monkeypatch.setattr(core.scenario, "_knowledge", StubIndex())
    context = _context("protected", "knowledge-op-fixture")
    fixture = ControlledFixture(surface="document", content="Documento neutro de prueba.")
    assert client.portal is not None

    client.portal.call(core.scenario.install_fixture, context, fixture)
    articles: list[dict[str, Any]] = json.loads(
        client.portal.call(_search, core, context, "envío")
    )["articles"]

    assert all({"text", "source", "trust"} <= set(article) for article in articles)
    assert articles[0]["trust"] == "lab"
    assert articles[-1] == {
        "text": "Documento neutro de prueba.",
        "source": "lab:campaign",
        "trust": "untrusted",
    }


@pytest.mark.skipif(POSTGRES_URL is not None, reason="con Postgres responde el índice híbrido")
def test_without_postgres_search_knowledge_answers_with_keywords(client: TestClient) -> None:
    core = _core(client)
    assert client.portal is not None

    output = json.loads(
        client.portal.call(_search, core, _context("protected", "knowledge-op-sqlite"), "envío")
    )

    assert core.knowledge is None
    assert output["source"] == "knowledge:tienda"
    assert [article["source"] for article in output["articles"]] == ["knowledge:envios"]


@needs_postgres
def test_with_postgres_the_app_seeds_and_searches_the_hybrid_index(client: TestClient) -> None:
    core = _core(client)
    assert client.portal is not None
    assert core.knowledge is not None
    assert core.knowledge.ready

    output = json.loads(
        client.portal.call(
            _search, core, _context("protected", "knowledge-op-pg"), "¿Cuánto tarda el envío?"
        )
    )

    assert 0 < len(output["articles"]) <= 4
    assert {article["trust"] for article in output["articles"]} <= {"official", "lab"}
