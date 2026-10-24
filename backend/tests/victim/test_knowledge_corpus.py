from pathlib import Path

import pytest

from agent_zero.victim.knowledge_corpus import (
    MAX_CHUNK_CHARS,
    CorpusError,
    load_corpus,
    parse_document,
)
from tests.victim.knowledge_support import document, sample_corpus, write


def test_a_document_without_sections_is_one_chunk_with_its_header() -> None:
    text = document("envios", "Envíos", "knowledge:envios", "Llegan en 30 minutos.")

    [chunk] = parse_document(text, "laboratorio")

    assert chunk.id == "laboratorio/envios#0"
    assert (chunk.document_id, chunk.title, chunk.source) == (
        "envios",
        "Envíos",
        "knowledge:envios",
    )
    assert chunk.trust == "lab"
    assert chunk.content == "Llegan en 30 minutos."


def test_each_second_level_section_is_a_chunk_that_keeps_its_heading() -> None:
    body = "Intro.\n\n## Pagos\nCon tarjeta.\n\n## Zonas\nEn Caracas."

    chunks = parse_document(document("faq", "FAQ", "https://example.com", body), "oficial")

    assert [chunk.content for chunk in chunks] == [
        "Intro.",
        "Pagos\nCon tarjeta.",
        "Zonas\nEn Caracas.",
    ]
    assert [chunk.id for chunk in chunks] == ["oficial/faq#0", "oficial/faq#1", "oficial/faq#2"]
    assert {chunk.trust for chunk in chunks} == {"official"}


def test_a_long_section_is_cut_by_paragraphs_without_overlap() -> None:
    paragraphs = [f"Párrafo {n}. " + "texto " * 60 for n in range(8)]
    body = "## Larga\n" + "\n\n".join(paragraphs)

    chunks = parse_document(document("larga", "Larga", "knowledge:larga", body), "senuelo")

    assert len(chunks) > 1
    assert all(len(chunk.content) <= MAX_CHUNK_CHARS + len("Larga\n") for chunk in chunks)
    assert all(chunk.content.startswith("Larga\n") for chunk in chunks)
    joined = "".join(chunk.content for chunk in chunks)
    assert all(joined.count(f"Párrafo {n}.") == 1 for n in range(8))


def test_the_hash_changes_with_anything_the_model_sees() -> None:
    [base] = parse_document(document("a", "Título", "knowledge:a", "Texto."), "laboratorio")
    [other_text] = parse_document(document("a", "Título", "knowledge:a", "Otro."), "laboratorio")
    [other_title] = parse_document(document("a", "Otro", "knowledge:a", "Texto."), "laboratorio")
    [same] = parse_document(document("a", "Título", "knowledge:a", "Texto."), "laboratorio")

    assert base.content_hash == same.content_hash
    assert len({base.content_hash, other_text.content_hash, other_title.content_hash}) == 3


@pytest.mark.parametrize(
    "text",
    [
        "sin encabezado",
        "---\nid: a\ntitle: A\nsource: s\n",
        "---\nid: a\ntitle: A\n---\nTexto.",
        "---\nid: A B\ntitle: A\nsource: s\n---\nTexto.",
        "---\nid: a\ntitle: A\nsource: s\n---\n\n",
        "---\nesto no es un campo\n---\nTexto.",
    ],
)
def test_a_malformed_document_is_rejected(text: str) -> None:
    with pytest.raises(CorpusError):
        parse_document(text, "laboratorio")


def test_an_unknown_collection_is_rejected() -> None:
    with pytest.raises(CorpusError):
        parse_document(document("a", "A", "s", "Texto."), "pedidos")


def test_the_collection_comes_from_the_folder_and_missing_folders_add_nothing(
    tmp_path: Path,
) -> None:
    assert load_corpus(tmp_path) == []
    (tmp_path / "oficial").mkdir()
    assert load_corpus(tmp_path) == []

    chunks = load_corpus(sample_corpus(tmp_path))

    assert {(chunk.collection, chunk.document_id) for chunk in chunks} == {
        ("oficial", "cobertura"),
        ("laboratorio", "reembolsos"),
        ("senuelo", "reembolsos"),
    }


def test_readme_and_private_files_are_not_documents(tmp_path: Path) -> None:
    write(tmp_path, "oficial", "cobertura", "Texto.")
    (tmp_path / "oficial" / "README.md").write_text("Notas del equipo", encoding="utf-8")
    (tmp_path / "oficial" / "_borrador.md").write_text("Sin terminar", encoding="utf-8")

    assert [chunk.document_id for chunk in load_corpus(tmp_path)] == ["cobertura"]


def test_two_files_with_the_same_id_in_a_collection_are_rejected(tmp_path: Path) -> None:
    write(tmp_path, "oficial", "cobertura", "Texto.")
    duplicate = tmp_path / "oficial" / "otro.md"
    duplicate.write_text(document("cobertura", "Otra", "s", "Más."), encoding="utf-8")

    with pytest.raises(CorpusError, match="repetido"):
        load_corpus(tmp_path)
