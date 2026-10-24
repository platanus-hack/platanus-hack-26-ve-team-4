import math
from pathlib import Path

from agent_zero.config import Settings
from agent_zero.victim.knowledge_embedder import (
    LOCAL_MODEL,
    FakeEmbedder,
    LocalEmbedder,
    build_embedder,
)
from agent_zero.victim.knowledge_models import EMBEDDING_DIMENSION


def _cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def test_the_fake_embedder_is_deterministic_normalized_and_of_the_table_dimension() -> None:
    first, again, empty = FakeEmbedder().embed(["Mi pedido no llega", "Mi pedido no llega", ""])

    assert first == again
    assert len(first) == EMBEDDING_DIMENSION
    assert math.isclose(math.sqrt(sum(v * v for v in first)), 1.0)
    assert math.isclose(math.sqrt(sum(v * v for v in empty)), 1.0)


def test_the_fake_embedder_brings_texts_with_shared_words_closer() -> None:
    query, related, unrelated = FakeEmbedder().embed(
        ["reembolso del pedido", "el reembolso se aprueba", "horario de farmacias"]
    )

    assert _cosine(query, related) > _cosine(query, unrelated)


def test_the_settings_choose_the_embedder_without_loading_the_model(tmp_path: Path) -> None:
    fake = build_embedder(Settings(data_dir=tmp_path, knowledge_embedder="fake"))
    local = build_embedder(Settings(data_dir=tmp_path, knowledge_embedder="local"))

    assert isinstance(fake, FakeEmbedder)
    assert isinstance(local, LocalEmbedder)
    assert local.model == LOCAL_MODEL
    assert local.dimension == EMBEDDING_DIMENSION
    # Construirlo no descarga nada: el modelo se carga en el primer `embed`.
    assert not (tmp_path / "models").exists()
