import pytest

from agent_zero.victim.knowledge import KNOWLEDGE
from agent_zero.victim.knowledge_search import (
    KNOWLEDGE_SOURCE,
    keyword_articles,
    knowledge_output,
)

pytestmark = pytest.mark.requirement("CORE-08")


class StubIndex:
    def __init__(self, ready: bool = True) -> None:
        self.ready = ready
        self.calls: list[tuple[str, tuple[str, ...]]] = []

    async def search(self, query: str, collections: tuple[str, ...]) -> list[dict[str, str]]:
        self.calls.append((query, collections))
        return [{"text": "fragmento", "source": "knowledge:envios", "trust": "lab"}]


def test_the_keyword_search_is_the_one_from_before() -> None:
    articles = keyword_articles("¿Dónde viene mi DELIVERY? Quiero un reembolso")

    by_slug = {article.slug: article.answer for article in KNOWLEDGE}
    assert articles == [
        {"text": by_slug["envios"], "source": "knowledge:envios"},
        {"text": by_slug["reembolsos"], "source": "knowledge:reembolsos"},
    ]
    assert keyword_articles("hola") == []


async def test_without_index_the_output_uses_keywords() -> None:
    output = await knowledge_output("¿Cuánto tarda el envío?", "protected", None)

    assert output == {
        "articles": keyword_articles("¿Cuánto tarda el envío?"),
        "source": KNOWLEDGE_SOURCE,
    }


async def test_an_index_that_did_not_start_falls_back_to_keywords() -> None:
    index = StubIndex(ready=False)

    output = await knowledge_output("reembolso", "honeypot", index)

    assert index.calls == []
    assert output["articles"] == keyword_articles("reembolso")


@pytest.mark.parametrize(
    ("environment", "collections"),
    [
        ("protected", ("oficial", "laboratorio")),
        ("validation", ("oficial", "laboratorio")),
        ("honeypot", ("oficial", "senuelo")),
    ],
)
async def test_the_index_searches_only_the_collections_of_the_environment(
    environment: str, collections: tuple[str, ...]
) -> None:
    index = StubIndex()

    output = await knowledge_output("envío", environment, index)

    assert index.calls == [("envío", collections)]
    assert output["source"] == KNOWLEDGE_SOURCE
    assert all({"text", "source", "trust"} <= set(article) for article in output["articles"])


async def test_an_unknown_environment_is_not_searched() -> None:
    with pytest.raises(ValueError, match="colecciones"):
        await knowledge_output("envío", "otro", StubIndex())
