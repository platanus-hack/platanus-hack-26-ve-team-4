"""Tabla `knowledge_chunks` de la base `<base>_knowledge`, solo en Postgres con pgvector."""

from pgvector.sqlalchemy import Vector
from sqlalchemy import Computed, Index, String, Text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

EMBEDDING_DIMENSION = 384


class KnowledgeBase(DeclarativeBase):
    """Propia: el `create_all` de las otras bases, también en SQLite, nunca crea esta tabla."""


class KnowledgeChunkRecord(KnowledgeBase):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        Index("knowledge_chunks_tsv", "tsv", postgresql_using="gin"),
        Index("knowledge_chunks_collection", "collection"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    collection: Mapped[str] = mapped_column(String(40))
    document_id: Mapped[str] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text)
    trust: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(200))
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSION))
    tsv: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('spanish', title || ' ' || content)", persisted=True),
    )
