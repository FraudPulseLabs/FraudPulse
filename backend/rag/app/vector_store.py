"""Vector store.

A small FAISS-backed store for chunk embeddings. It uses ``IndexFlatIP``
(inner product); because embeddings are L2-normalized, inner product equals
cosine similarity. The store keeps chunk objects parallel to the index so a
search returns the original text plus its similarity score.

Supports add, search, and save/load (FAISS binary index + JSON sidecar).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from rag.config import (
    CHUNKS_PATH,
    EMBEDDING_DIM,
    EMBEDDING_MODEL,
    FAISS_INDEX_PATH,
    INDEX_DIR,
    INDEX_META_PATH,
)
from rag.app.chunking import Chunk

if TYPE_CHECKING:  # pragma: no cover - typing only
    import faiss


def _import_faiss():
    try:
        import faiss

        return faiss
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "The vector store requires 'faiss-cpu'. Install it with "
            "`pip install faiss-cpu`."
        ) from exc


@dataclass(slots=True)
class SearchResult:
    """A retrieved chunk and its cosine similarity to the query."""

    chunk: Chunk
    score: float
    rank: int


class VectorStore:
    """FAISS ``IndexFlatIP`` (cosine) store over chunk embeddings."""

    def __init__(
        self,
        dimension: int = EMBEDDING_DIM,
        embedding_model: str = EMBEDDING_MODEL,
    ) -> None:
        self.dimension = dimension
        self.embedding_model = embedding_model
        self._faiss = _import_faiss()
        self.index = self._faiss.IndexFlatIP(dimension)
        self.chunks: list[Chunk] = []

    # ------------------------------------------------------------------ #
    # Mutation
    # ------------------------------------------------------------------ #
    def add(self, chunks: list[Chunk], embeddings: np.ndarray) -> None:
        """Add chunks and their (n, dim) normalized embedding matrix."""
        if len(chunks) != embeddings.shape[0]:
            raise ValueError(
                f"chunks ({len(chunks)}) and embeddings "
                f"({embeddings.shape[0]}) length mismatch"
            )
        if embeddings.shape[0] == 0:
            return
        if embeddings.shape[1] != self.dimension:
            raise ValueError(
                f"embedding dim {embeddings.shape[1]} != index dim "
                f"{self.dimension}"
            )
        self.index.add(np.ascontiguousarray(embeddings, dtype=np.float32))
        self.chunks.extend(chunks)

    # ------------------------------------------------------------------ #
    # Query
    # ------------------------------------------------------------------ #
    def search(
        self, query_embedding: np.ndarray, top_k: int
    ) -> list[SearchResult]:
        """Return the ``top_k`` most similar chunks for a query embedding."""
        if self.index.ntotal == 0:
            return []

        query = np.ascontiguousarray(
            query_embedding.reshape(1, -1), dtype=np.float32
        )
        k = min(top_k, self.index.ntotal)
        scores, indices = self.index.search(query, k)

        results: list[SearchResult] = []
        for rank, (score, idx) in enumerate(zip(scores[0], indices[0])):
            if idx < 0:
                continue
            results.append(
                SearchResult(
                    chunk=self.chunks[int(idx)],
                    score=float(score),
                    rank=rank,
                )
            )
        return results

    @property
    def size(self) -> int:
        return int(self.index.ntotal)

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #
    def save(
        self,
        index_path: Path = FAISS_INDEX_PATH,
        chunks_path: Path = CHUNKS_PATH,
        meta_path: Path = INDEX_META_PATH,
    ) -> None:
        """Persist the FAISS index, the chunk sidecar, and metadata."""
        INDEX_DIR.mkdir(parents=True, exist_ok=True)
        self._faiss.write_index(self.index, str(index_path))
        chunks_path.write_text(
            json.dumps([c.to_dict() for c in self.chunks], indent=2),
            encoding="utf-8",
        )
        meta_path.write_text(
            json.dumps(
                {
                    "dimension": self.dimension,
                    "embedding_model": self.embedding_model,
                    "num_chunks": len(self.chunks),
                    "index_type": "IndexFlatIP",
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    @classmethod
    def load(
        cls,
        index_path: Path = FAISS_INDEX_PATH,
        chunks_path: Path = CHUNKS_PATH,
        meta_path: Path = INDEX_META_PATH,
    ) -> "VectorStore":
        """Load a previously saved vector store from disk."""
        if not index_path.exists() or not chunks_path.exists():
            raise FileNotFoundError(
                f"Vector store not found at {index_path}. Build it first with "
                "`python -m rag.scripts.build_vector_db`."
            )

        meta = {}
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))

        store = cls(
            dimension=meta.get("dimension", EMBEDDING_DIM),
            embedding_model=meta.get("embedding_model", EMBEDDING_MODEL),
        )
        store.index = store._faiss.read_index(str(index_path))
        raw_chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
        store.chunks = [Chunk.from_dict(d) for d in raw_chunks]
        return store


__all__ = ["VectorStore", "SearchResult"]
