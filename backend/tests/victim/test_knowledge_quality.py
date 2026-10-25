"""Calidad mínima con el modelo real. Opcional: descarga el modelo, no corre en la CI.

Correr con Postgres y pgvector:
    AGENT_ZERO_KNOWLEDGE_QUALITY=1 AGENT_ZERO_TEST_DATABASE_URL=... uv run pytest -s \
        tests/victim/test_knowledge_quality.py
"""

import os
from pathlib import Path

import pytest

from agent_zero.config import Settings
from agent_zero.victim.knowledge_collections import collections_for
from agent_zero.victim.knowledge_corpus import load_corpus
from agent_zero.victim.knowledge_embedder import LocalEmbedder
from agent_zero.victim.knowledge_index import KnowledgeIndex
from tests.victim.knowledge_support import needs_postgres

QUALITY_FLAG = "AGENT_ZERO_KNOWLEDGE_QUALITY"
MODEL_CACHE = Path(
    os.environ.get("AGENT_ZERO_KNOWLEDGE_MODEL_CACHE", Path.home() / ".cache" / "agent-zero")
)
TARGET = 12

# Preguntas legítimas de clientes y los documentos que las responden (colección/documento).
CASES: tuple[tuple[str, frozenset[str]], ...] = tuple(
    (question, frozenset(expected))
    for question, expected in (
        ("me llegó la comida fría, ¿qué hago?", {"laboratorio/cambios"}),
        ("¿cuánto se demora en llegar lo que pedí?", {"laboratorio/envios"}),
        ("quiero que me devuelvan la plata de una orden", {"laboratorio/reembolsos"}),
        ("me faltó un producto en la bolsa", {"laboratorio/cambios"}),
        ("¿puedo pagar con Zelle o con Pago Móvil?", {"oficial/metodos-de-pago"}),
        ("la app me dice que no encuentra mi pago", {"oficial/metodos-de-pago"}),
        (
            "¿cómo cancelo una orden sin que me cobren?",
            {"oficial/terminos-cancelaciones-y-reclamos"},
        ),
        ("¿por qué me cancelaron el pedido?", {"oficial/motivos-de-cancelacion"}),
        (
            "¿en qué ciudades hay servicio de Yummi?",
            {"oficial/servicios-y-cobertura", "oficial/como-hacer-un-pedido"},
        ),
        ("¿dónde veo en qué estado va mi pedido?", {"oficial/seguimiento-y-cambios-de-pedido"}),
        ("el repartidor no llega, ¿cómo lo llamo?", {"oficial/seguimiento-y-cambios-de-pedido"}),
        ("¿hasta qué hora puedo pedir un sábado?", {"oficial/horarios-y-disponibilidad"}),
        ("¿de qué depende lo que cuesta el delivery?", {"oficial/como-hacer-un-pedido"}),
        ("¿qué hacen con mis datos personales?", {"oficial/privacidad-y-datos"}),
        (
            "¿puedo cambiar la dirección después de pedir?",
            {"oficial/seguimiento-y-cambios-de-pedido"},
        ),
    )
)

pytestmark = [
    needs_postgres,
    pytest.mark.skipif(
        os.environ.get(QUALITY_FLAG) != "1",
        reason=f"descarga el modelo de vectores (unos 220 MB): exportar {QUALITY_FLAG}=1",
    ),
]


async def test_the_expected_document_is_in_the_top_four_for_most_questions(
    settings: Settings,
) -> None:
    assert settings.knowledge_database_url is not None
    documents = {
        chunk.content: f"{chunk.collection}/{chunk.document_id}" for chunk in load_corpus()
    }
    index = KnowledgeIndex(settings.knowledge_database_url, LocalEmbedder(MODEL_CACHE))
    hits = 0
    try:
        await index.initialize()
        for question, expected in CASES:
            articles = await index.search(question, collections_for("protected"))
            found = [documents[article["text"]] for article in articles]
            hit = bool(expected & set(found))
            hits += hit
            print(f"{'OK ' if hit else 'NO '} {question} -> {found}")
    finally:
        await index.dispose()

    print(f"{hits}/{len(CASES)} con el documento esperado entre los 4 primeros")
    assert len(CASES) == 15
    assert hits >= TARGET
