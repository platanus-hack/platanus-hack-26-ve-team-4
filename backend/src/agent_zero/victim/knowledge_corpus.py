"""Corpus de la base de conocimiento: un Markdown por documento, fragmentado por sección."""

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

from agent_zero.victim.knowledge_collections import COLLECTIONS, TRUST_BY_COLLECTION

CORPUS_ROOT = Path(__file__).resolve().parent / "knowledge_docs"
MAX_CHUNK_CHARS = 1200
REQUIRED_FIELDS = ("id", "title", "source")
_DOCUMENT_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,79}$")
_FIELD = re.compile(r"^([a-z_]+):\s*(.*)$")


class CorpusError(ValueError):
    pass


@dataclass(frozen=True)
class KnowledgeChunk:
    id: str  # "<coleccion>/<documento>#<n>"
    collection: str
    document_id: str
    title: str
    source: str
    trust: str
    content: str
    captured_at: str | None = None

    @property
    def content_hash(self) -> str:
        """Cambia si cambia cualquier cosa que el modelo ve del fragmento."""
        canonical = json.dumps(
            [self.title, self.source, self.trust, self.content], ensure_ascii=False
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _split_header(text: str, name: str) -> tuple[dict[str, str], str]:
    lines = text.replace("\r\n", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        raise CorpusError(f"{name}: falta el encabezado entre líneas ---.")
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        raise CorpusError(f"{name}: el encabezado no se cierra con ---.") from None
    header: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip():
            continue
        match = _FIELD.match(line.strip())
        if match is None:
            raise CorpusError(f"{name}: línea de encabezado inválida.")
        header[match[1]] = match[2].strip()
    missing = [field for field in REQUIRED_FIELDS if not header.get(field)]
    if missing:
        raise CorpusError(f"{name}: faltan los campos {', '.join(missing)}.")
    if not _DOCUMENT_ID.match(header["id"]):
        raise CorpusError(f"{name}: el id debe ser minúsculas, números y guiones.")
    return header, "\n".join(lines[end + 1 :])


def _sections(body: str) -> list[tuple[str, str]]:
    """Pares (título de sección, texto); el texto antes del primer ## va sin título."""
    sections: list[tuple[str, list[str]]] = [("", [])]
    for line in body.split("\n"):
        if line.startswith("## "):
            sections.append((line[3:].strip(), []))
        else:
            sections[-1][1].append(line)
    return [(heading, "\n".join(lines).strip()) for heading, lines in sections]


def _pieces(text: str) -> list[str]:
    """Corta por párrafos un texto largo, sin solapamiento; un párrafo nunca se parte."""
    if len(text) <= MAX_CHUNK_CHARS:
        return [text]
    pieces: list[str] = []
    current = ""
    for paragraph in (p.strip() for p in re.split(r"\n\s*\n", text)):
        if not paragraph:
            continue
        joined = f"{current}\n\n{paragraph}" if current else paragraph
        if current and len(joined) > MAX_CHUNK_CHARS:
            pieces.append(current)
            current = paragraph
        else:
            current = joined
    if current:
        pieces.append(current)
    return pieces


def parse_document(text: str, collection: str, name: str = "documento") -> list[KnowledgeChunk]:
    if collection not in TRUST_BY_COLLECTION:
        raise CorpusError(f"{name}: colección desconocida {collection!r}.")
    header, body = _split_header(text, name)
    contents: list[str] = []
    for heading, section in _sections(body):
        if not section:
            continue
        for piece in _pieces(section):
            contents.append(f"{heading}\n{piece}" if heading else piece)
    if not contents:
        raise CorpusError(f"{name}: el documento no tiene contenido.")
    return [
        KnowledgeChunk(
            id=f"{collection}/{header['id']}#{number}",
            collection=collection,
            document_id=header["id"],
            title=header["title"],
            source=header["source"],
            trust=TRUST_BY_COLLECTION[collection],
            content=content,
            captured_at=header.get("captured_at") or None,
        )
        for number, content in enumerate(contents)
    ]


def _is_document(path: Path) -> bool:
    return path.is_file() and not path.name.startswith(("_", ".")) and path.stem.upper() != "README"


def load_corpus(root: Path = CORPUS_ROOT) -> list[KnowledgeChunk]:
    """Lee las tres colecciones; una carpeta ausente o vacía no aporta fragmentos."""
    chunks: list[KnowledgeChunk] = []
    for collection in COLLECTIONS:
        seen: dict[str, str] = {}
        folder = root / collection
        if not folder.is_dir():
            continue
        for path in sorted(p for p in folder.glob("*.md") if _is_document(p)):
            name = f"{collection}/{path.name}"
            document = parse_document(path.read_text(encoding="utf-8"), collection, name)
            document_id = document[0].document_id
            if document_id in seen:
                raise CorpusError(f"{name}: id repetido con {seen[document_id]}.")
            seen[document_id] = name
            chunks.extend(document)
    return chunks
