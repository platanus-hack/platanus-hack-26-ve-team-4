from agent_zero.shared.database import AppBase
from agent_zero.victim.knowledge_models import (
    EMBEDDING_DIMENSION,
    KnowledgeBase,
    KnowledgeChunkRecord,
)
from agent_zero.victim.store_models import StoreBase


def test_the_knowledge_table_lives_only_in_its_own_metadata() -> None:
    assert "knowledge_chunks" in KnowledgeBase.metadata.tables
    assert "knowledge_chunks" not in AppBase.metadata.tables
    assert "knowledge_chunks" not in StoreBase.metadata.tables


def test_the_table_keeps_provenance_hash_model_vector_and_text_search() -> None:
    columns = KnowledgeChunkRecord.__table__.columns

    assert {"collection", "source", "trust", "content_hash", "model", "embedding", "tsv"} <= set(
        columns.keys()
    )
    assert getattr(columns["embedding"].type, "dim", None) == EMBEDDING_DIMENSION
    assert columns["tsv"].computed is not None
