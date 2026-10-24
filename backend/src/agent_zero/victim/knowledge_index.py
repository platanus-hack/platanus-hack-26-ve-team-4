"""Índice de conocimiento en `<base>_knowledge`: siembra idempotente y búsqueda híbrida."""

import asyncio
from dataclasses import dataclass
from pathlib import Path

from pgvector.sqlalchemy import Vector
from sqlalchemy import String, bindparam, delete, select, text
from sqlalchemy.dialects.postgresql import ARRAY, insert
from sqlalchemy.ext.asyncio import AsyncConnection

from agent_zero.config import Settings
from agent_zero.shared.database import Database, ensure_database, is_postgres
from agent_zero.victim.knowledge_corpus import CORPUS_ROOT, KnowledgeChunk, load_corpus
from agent_zero.victim.knowledge_embedder import Embedder, build_embedder
from agent_zero.victim.knowledge_models import (
    EMBEDDING_DIMENSION,
    KnowledgeBase,
    KnowledgeChunkRecord,
)

# Distinta de WRITE_LOCK_KEY: dos procesos que arrancan a la vez no siembran en paralelo.
KNOWLEDGE_LOCK_KEY = 0x6B6E_6F77_6C65
MAX_ARTICLES = 4
RRF_K = 60
# Lexemas sin operadores de tsquery ni barras: se combinan con O sin alterar la sintaxis.
SAFE_LEXEME = r"^[^&|!():<>*'\\\s]+$"

# Fusión por rango recíproco de dos listas: palabras clave (tsvector en español, términos con O)
# y similitud semántica exacta (distancia coseno). Cada lista aporta 1 / (k + rango).
HYBRID_QUERY = text(
    """
WITH q AS (
  SELECT to_tsquery('simple', COALESCE(string_agg(lexeme, ' | '), '')) AS tsq
  FROM unnest(tsvector_to_array(to_tsvector('spanish', :query))) AS lexeme
  WHERE lexeme ~ :safe_lexeme
),
lex AS (
  SELECT c.id, row_number() OVER (ORDER BY ts_rank(c.tsv, q.tsq) DESC, c.id) AS r
  FROM knowledge_chunks c, q
  WHERE c.collection = ANY(:collections) AND c.tsv @@ q.tsq
  ORDER BY r LIMIT 20
),
sem AS (
  SELECT c.id, row_number() OVER (ORDER BY c.embedding <=> :embedding, c.id) AS r
  FROM knowledge_chunks c
  WHERE c.collection = ANY(:collections)
  ORDER BY r LIMIT 20
)
SELECT c.id, c.content, c.source, c.trust,
       COALESCE(1.0 / (:k + lex.r), 0) + COALESCE(1.0 / (:k + sem.r), 0) AS score
FROM lex FULL OUTER JOIN sem USING (id)
JOIN knowledge_chunks c USING (id)
ORDER BY score DESC, c.id
LIMIT :limit
"""
).bindparams(
    bindparam("collections", type_=ARRAY(String)),
    bindparam("embedding", type_=Vector(EMBEDDING_DIMENSION)),
)


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

    async def search(
        self, query: str, collections: tuple[str, ...], limit: int = MAX_ARTICLES
    ) -> list[dict[str, str]]:
        """Fragmentos de esas colecciones, con su procedencia; nunca de otra colección."""
        if not collections:
            return []
        [vector] = await self.embed([query])
        async with self.database.sessions() as db:
            rows = await db.execute(
                HYBRID_QUERY,
                {
                    "query": query,
                    "safe_lexeme": SAFE_LEXEME,
                    "collections": list(collections),
                    "embedding": vector,
                    "k": RRF_K,
                    "limit": limit,
                },
            )
            return [
                {"text": row.content, "source": row.source, "trust": row.trust}
                for row in rows
                if row.score > 0
            ]

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
