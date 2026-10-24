"""Vectorizadores de la base de conocimiento: el modelo local y uno falso para los tests."""

import hashlib
import math
import re
import threading
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from fastembed import TextEmbedding

from agent_zero.config import Settings
from agent_zero.victim.knowledge_models import EMBEDDING_DIMENSION

LOCAL_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
_WORD = re.compile(r"\w+")
_load_lock = threading.Lock()


class Embedder(Protocol):
    model: str
    dimension: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


def _normalized(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        # La distancia coseno con un vector nulo no está definida: se usa un eje fijo.
        return [1.0, *([0.0] * (len(vector) - 1))]
    return [value / norm for value in vector]


class FakeEmbedder:
    """Determinista y sin red: cada palabra suma ±1 en una posición derivada de su hash."""

    model = "fake-hash-words-v1"
    dimension = EMBEDDING_DIMENSION

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._one(text) for text in texts]

    def _one(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        for word in _WORD.findall(text.casefold()):
            digest = hashlib.sha256(word.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            vector[index] += 1.0 if digest[4] % 2 == 0 else -1.0
        return _normalized(vector)


@lru_cache(maxsize=2)
def _load_model(cache_dir: str) -> TextEmbedding:
    return TextEmbedding(LOCAL_MODEL, cache_dir=cache_dir)


class LocalEmbedder:
    """El modelo multilingüe con fastembed; se descarga la primera vez a `cache_dir`."""

    model = LOCAL_MODEL
    dimension = EMBEDDING_DIMENSION

    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = cache_dir

    def load(self) -> TextEmbedding:
        # Una sola carga por proceso aunque varios hilos pidan vectores a la vez.
        with _load_lock:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            return _load_model(str(self._cache_dir))

    def embed(self, texts: list[str]) -> list[list[float]]:
        model = self.load()
        return [[float(value) for value in vector] for vector in model.embed(texts)]


def build_embedder(settings: Settings) -> Embedder:
    if settings.knowledge_embedder == "fake":
        return FakeEmbedder()
    return LocalEmbedder(settings.knowledge_model_dir)
