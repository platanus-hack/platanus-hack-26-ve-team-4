"""§4.3 y §4.2 del plan RAG: nada de la tienda en el índice y cada entorno solo ve lo suyo."""

import re
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from agent_zero.config import Settings
from agent_zero.victim.fixtures import ORDERS, SYNTHETIC_CUSTOMER_IDS, customer_ids
from agent_zero.victim.honeypot_fixtures import HONEYPOT_ORDERS, decoy_delivery_address
from agent_zero.victim.knowledge_collections import COLLECTIONS_BY_ENVIRONMENT, collections_for
from agent_zero.victim.knowledge_corpus import CORPUS_ROOT, load_corpus
from agent_zero.victim.knowledge_embedder import FakeEmbedder
from agent_zero.victim.knowledge_index import KnowledgeIndex
from tests.victim.knowledge_support import needs_postgres, sample_corpus

pytestmark = pytest.mark.requirement("CORE-08")

ORDER_ID = re.compile(r"\b(?:[A-C]-\d{4}|D-\d{4,})\b")
CANARY = re.compile(r"AZ[PH]_")
QUESTIONS = (
    "¿Cuánto tarda en llegar mi pedido?",
    "Quiero un reembolso de mi orden",
    "Me faltó un producto",
    "¿Puedo pagar con Pago Móvil?",
    "¿Cómo cancelo una orden?",
    "¿En qué ciudades opera Yummi?",
)
FORBIDDEN_TRUST = {"protected": "decoy", "validation": "decoy", "honeypot": "lab"}


def _store_values() -> set[str]:
    """Datos de pedidos y clientes, protegidos y del señuelo: nunca entran al índice."""
    values = set(customer_ids(500))
    for order in ORDERS.values():
        values |= {order.customer_email, order.pickup_address, order.delivery_address}
    values |= {decoy.pickup_address for decoy in HONEYPOT_ORDERS}
    values |= {decoy_delivery_address(customer) for customer in customer_ids(500)}
    return values


def test_no_chunk_of_the_real_corpus_holds_store_data() -> None:
    chunks = load_corpus()
    values = _store_values()

    assert chunks
    for chunk in chunks:
        text = f"{chunk.title}\n{chunk.source}\n{chunk.content}"
        assert ORDER_ID.search(text) is None, chunk.id
        assert CANARY.search(text) is None, chunk.id
        assert not any(value in text for value in values), chunk.id
        assert not any(customer in text for customer in SYNTHETIC_CUSTOMER_IDS), chunk.id


def test_the_corpus_is_only_markdown_files_of_the_three_collections() -> None:
    folders = {path.name for path in CORPUS_ROOT.iterdir() if path.is_dir()}

    assert folders <= {"oficial", "laboratorio", "senuelo"}
    assert all(path.suffix == ".md" for path in CORPUS_ROOT.rglob("*") if path.is_file())


def test_the_official_collection_is_seen_by_the_three_environments() -> None:
    assert set(COLLECTIONS_BY_ENVIRONMENT) == {"protected", "validation", "honeypot"}
    assert all("oficial" in collections_for(name) for name in COLLECTIONS_BY_ENVIRONMENT)


async def _seeded(url: str, root: Path) -> KnowledgeIndex:
    index = KnowledgeIndex(url, FakeEmbedder(), root)
    await index.initialize()
    return index


@pytest.fixture
async def real_index(settings: Settings) -> AsyncIterator[KnowledgeIndex]:
    assert settings.knowledge_database_url is not None
    index = await _seeded(settings.knowledge_database_url, CORPUS_ROOT)
    try:
        yield index
    finally:
        await index.dispose()


@needs_postgres
@pytest.mark.parametrize("environment", sorted(FORBIDDEN_TRUST))
async def test_no_search_crosses_the_decoy_and_lab_boundary(
    real_index: KnowledgeIndex, environment: str
) -> None:
    for question in QUESTIONS:
        articles = await real_index.search(question, collections_for(environment))

        assert articles, question
        assert FORBIDDEN_TRUST[environment] not in {article["trust"] for article in articles}


@needs_postgres
@pytest.mark.parametrize("environment", sorted(FORBIDDEN_TRUST))
async def test_each_environment_finds_the_official_collection(
    settings: Settings, tmp_path: Path, environment: str
) -> None:
    assert settings.knowledge_database_url is not None
    index = await _seeded(settings.knowledge_database_url, sample_corpus(tmp_path))
    try:
        articles = await index.search("¿Yummi entrega en Caracas?", collections_for(environment))
    finally:
        await index.dispose()

    assert articles[0]["trust"] == "official"
    assert articles[0]["source"] == "https://example.com/cobertura"
