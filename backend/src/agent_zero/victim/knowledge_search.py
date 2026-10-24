"""Resultado de `search_knowledge`: búsqueda híbrida con Postgres, palabras clave sin él."""

from typing import Any, Protocol

from agent_zero.victim.knowledge import KNOWLEDGE
from agent_zero.victim.knowledge_collections import collections_for

KNOWLEDGE_SOURCE = "knowledge:tienda"
# Lo que ve el modelo: el señuelo se presenta como el laboratorio, para que una sesión desviada
# no lo reconozca por la etiqueta. `decoy` queda en el índice y en sus pruebas de aislamiento.
VISIBLE_TRUST = {"decoy": "lab"}


class KnowledgeSearch(Protocol):
    ready: bool

    async def search(self, query: str, collections: tuple[str, ...]) -> list[dict[str, str]]: ...


def keyword_articles(query: str) -> list[dict[str, str]]:
    """La búsqueda de siempre, sin cambios: modo SQLite o índice que no arrancó."""
    folded = query.casefold()
    return [
        {"text": article.answer, "source": f"knowledge:{article.slug}"}
        for article in KNOWLEDGE
        if any(word in folded for word in article.keywords)
    ]


async def knowledge_output(
    query: str, environment: str, knowledge: KnowledgeSearch | None
) -> dict[str, Any]:
    """Cada entorno busca solo en sus colecciones; nunca en datos de la tienda."""
    if knowledge is not None and knowledge.ready:
        articles = [
            article | {"trust": VISIBLE_TRUST.get(article["trust"], article["trust"])}
            for article in await knowledge.search(query, collections_for(environment))
        ]
    else:
        articles = keyword_articles(query)
    return {"articles": articles, "source": KNOWLEDGE_SOURCE}
