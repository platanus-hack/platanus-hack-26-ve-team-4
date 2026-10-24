from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy import func, select, text

from agent_zero.config import Settings
from agent_zero.victim.knowledge_embedder import FakeEmbedder
from agent_zero.victim.knowledge_index import KnowledgeIndex, build_knowledge_index
from agent_zero.victim.knowledge_models import KnowledgeChunkRecord
from tests.victim.knowledge_support import needs_postgres, sample_corpus, write


def test_without_postgres_there_is_no_index(tmp_path: Path) -> None:
    assert build_knowledge_index(Settings(data_dir=tmp_path)) is None
    with pytest.raises(ValueError, match="Postgres"):
        KnowledgeIndex("sqlite+aiosqlite://", FakeEmbedder())


@pytest.fixture
async def index(settings: Settings, tmp_path: Path) -> AsyncIterator[KnowledgeIndex]:
    url = settings.knowledge_database_url
    assert url is not None
    knowledge = KnowledgeIndex(url, FakeEmbedder(), sample_corpus(tmp_path / "corpus"))
    try:
        yield knowledge
    finally:
        await knowledge.dispose()


async def _rows(index: KnowledgeIndex) -> dict[str, str]:
    async with index.database.sessions() as db:
        rows = await db.execute(select(KnowledgeChunkRecord.id, KnowledgeChunkRecord.content_hash))
        return {row.id: row.content_hash for row in rows}


@needs_postgres
async def test_seeding_twice_leaves_the_same_chunks(index: KnowledgeIndex) -> None:
    first = await index.initialize()
    rows = await _rows(index)
    second = await index.initialize()

    assert (first.inserted, first.updated, first.deleted) == (3, 0, 0)
    assert (second.inserted, second.updated, second.deleted, second.unchanged) == (0, 0, 0, 3)
    assert await _rows(index) == rows
    assert index.ready


@needs_postgres
async def test_the_database_has_the_vector_extension(index: KnowledgeIndex) -> None:
    await index.initialize()

    async with index.database.sessions() as db:
        extension = await db.scalar(
            text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        )
        count = await db.scalar(select(func.count()).select_from(KnowledgeChunkRecord))

    assert extension == "vector"
    assert count == 3


@needs_postgres
async def test_changing_a_file_updates_only_its_chunks(
    index: KnowledgeIndex, tmp_path: Path
) -> None:
    await index.initialize()
    before = await _rows(index)
    write(tmp_path / "corpus", "laboratorio", "reembolsos", "Ahora hasta 15 USD.")

    report = await index.initialize()
    after = await _rows(index)

    assert (report.inserted, report.updated, report.deleted, report.unchanged) == (0, 1, 0, 2)
    assert after["laboratorio/reembolsos#0"] != before["laboratorio/reembolsos#0"]
    assert {k: v for k, v in after.items() if k != "laboratorio/reembolsos#0"} == {
        k: v for k, v in before.items() if k != "laboratorio/reembolsos#0"
    }


@needs_postgres
async def test_deleting_a_file_deletes_its_chunks(index: KnowledgeIndex, tmp_path: Path) -> None:
    await index.initialize()
    (tmp_path / "corpus" / "senuelo" / "reembolsos.md").unlink()

    report = await index.initialize()

    assert report.deleted == 1
    assert set(await _rows(index)) == {"oficial/cobertura#0", "laboratorio/reembolsos#0"}


@needs_postgres
async def test_a_new_model_recomputes_every_vector(settings: Settings, tmp_path: Path) -> None:
    class OtherModel(FakeEmbedder):
        model = "fake-otro-modelo"

    url = settings.knowledge_database_url
    assert url is not None
    corpus = sample_corpus(tmp_path / "corpus")
    for embedder, expected in ((FakeEmbedder(), 3), (OtherModel(), 3), (OtherModel(), 0)):
        knowledge = KnowledgeIndex(url, embedder, corpus)
        try:
            report = await knowledge.initialize()
        finally:
            await knowledge.dispose()
        assert report.inserted + report.updated == expected
