"""Corpus de prueba en tmp_path: los tests nunca dependen del corpus real ni de `oficial/`."""

import os
from pathlib import Path

import pytest

POSTGRES_URL = os.environ.get("AGENT_ZERO_TEST_DATABASE_URL")

needs_postgres = pytest.mark.skipif(
    POSTGRES_URL is None,
    reason="la base de conocimiento híbrida necesita AGENT_ZERO_TEST_DATABASE_URL (pgvector)",
)


def document(document_id: str, title: str, source: str, body: str) -> str:
    return f"---\nid: {document_id}\ntitle: {title}\nsource: {source}\n---\n{body}\n"


def write(root: Path, collection: str, document_id: str, body: str, **header: str) -> Path:
    folder = root / collection
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{document_id}.md"
    title = header.get("title", document_id.capitalize())
    source = header.get("source", f"knowledge:{document_id}")
    path.write_text(document(document_id, title, source, body), encoding="utf-8")
    return path


def sample_corpus(root: Path) -> Path:
    """Un documento por colección, con temas distintos para comprobar el aislamiento."""
    write(
        root,
        "oficial",
        "cobertura",
        "Yummy entrega en Caracas, Valencia y Maracaibo.",
        source="https://example.com/cobertura",
    )
    write(root, "laboratorio", "reembolsos", "Los reembolsos se aprueban hasta 20 USD.")
    write(root, "senuelo", "reembolsos", "Los reintegros del comercio aliado tardan un día.")
    return root
