"""Índice de conocimiento en `<base>_knowledge`: siembra idempotente y búsqueda híbrida."""

import asyncio
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import delete, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncConnection

from agent_zero.config import Settings
from agent_zero.shared.database import Database, ensure_database, is_postgres
from agent_zero.victim.knowledge_corpus import CORPUS_ROOT, KnowledgeChunk, load_corpus
from agent_zero.victim.knowledge_embedder import Embedder, build_embedder
from agent_zero.victim.knowledge_models import KnowledgeBase, KnowledgeChunkRecord

# Distinta de WRITE_LOCK_KEY: dos procesos que arrancan a la vez no siembran en paralelo.
KNOWLEDGE_LOCK_KEY = 0x6B6E_6F77_6C65


@dataclass(frozen=True)
class SeedReport:
    inserted: int
    updated: int
    deleted: int
    unchanged: int


class KnowledgeIndex:
    """De solo lectura en tiempo de ejecución: el reset y el snapshot de ronda no lo tocan."""

    def __init__(self, url: str, embedder: Embedder, root: Path = CORPUS_ROOT) -> None:
        if not is_postgres(url):
            raise ValueError("La base de conocimiento híbrida necesita Postgres.")
        self._url = url
        self._embedder = embedder
        self._root = root
        self.database = Database(url)
        self.ready = False

    @property
    def model(self) -> str:
        return self._embedder.model

    async def initialize(self) -> SeedReport:
        """Crea la base, la extensión y la tabla, y siembra el corpus de los archivos."""
        await ensure_database(self._url)
        chunks = load_corpus(self._root)
        async with self.database.engine.begin() as connection:
            await connection.execute(
                text("SELECT pg_advisory_xact_lock(:key)"), {"key": KNOWLEDGE_LOCK_KEY}
            )
            await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await connection.run_sync(KnowledgeBase.metadata.create_all)
            report = await self._seed(connection, chunks)
        self.ready = True
        return report

    async def _seed(self, connection: AsyncConnection, chunks: list[KnowledgeChunk]) -> SeedReport:
        record = KnowledgeChunkRecord
        rows = await connection.execute(select(record.id, record.content_hash, record.model))
        stored = {row.id: (row.content_hash, row.model) for row in rows}
        current = {chunk.id for chunk in chunks}
        changed = [
            chunk
            for chunk in chunks
            if stored.get(chunk.id) != (chunk.content_hash, self._embedder.model)
        ]
        vectors = await self.embed([chunk.content for chunk in changed]) if changed else []
        for chunk, vector in zip(changed, vectors, strict=True):
            values = {
                "collection": chunk.collection,
                "document_id": chunk.document_id,
                "title": chunk.title,
                "source": chunk.source,
                "trust": chunk.trust,
                "content": chunk.content,
                "content_hash": chunk.content_hash,
                "model": self._embedder.model,
                "embedding": vector,
            }
            statement = insert(record).values(id=chunk.id, **values)
            await connection.execute(
                statement.on_conflict_do_update(index_elements=[record.id], set_=values)
            )
        stale = set(stored) - current
        if stale:
            await connection.execute(delete(record).where(record.id.in_(stale)))
        inserted = sum(1 for chunk in changed if chunk.id not in stored)
        return SeedReport(
            inserted=inserted,
            updated=len(changed) - inserted,
            deleted=len(stale),
            unchanged=len(chunks) - len(changed),
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        # fastembed es síncrono: se ejecuta fuera del bucle de eventos.
        return await asyncio.to_thread(self._embedder.embed, texts)

    async def dispose(self) -> None:
        await self.database.dispose()


def build_knowledge_index(settings: Settings) -> KnowledgeIndex | None:
    """Sin Postgres no hay índice: `search_knowledge` sigue con las palabras clave."""
    url = settings.knowledge_database_url
    if url is None:
        return None
    return KnowledgeIndex(url, build_embedder(settings))
