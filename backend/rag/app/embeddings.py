"""Embeddings.

A thin, deterministic wrapper around ``sentence-transformers`` that turns text
into normalized dense vectors. Normalization (unit L2 norm) means the dot
product of two embeddings equals their cosine similarity, which pairs naturally
with a FAISS inner-product index.

The model (``all-MiniLM-L6-v2`` by default) runs locally on CPU, so no network
call is made at query time.
"""

from __future__ import annotations

import os

# Disable Hugging Face tokenizers' internal thread parallelism. Under a forking
# server (uvicorn --reload / multiple workers) it otherwise prints a fork
# warning and can leak a multiprocessing semaphore at shutdown
# ("resource_tracker: There appear to be N leaked semaphore objects").
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from functools import lru_cache
from typing import TYPE_CHECKING, Iterable

import numpy as np

from rag.config import EMBEDDING_DIM, EMBEDDING_MODEL, RANDOM_SEED

if TYPE_CHECKING:  # pragma: no cover - typing only
    from sentence_transformers import SentenceTransformer


@lru_cache(maxsize=2)
def _load_model(model_name: str) -> "SentenceTransformer":
    """Load (and cache) the sentence-transformers model.

    Imported lazily so the rest of the package can be imported without the
    heavy ML dependency present (e.g. in lightweight CI import checks).
    """
    try:
        import torch  # noqa: F401
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "Embeddings require 'sentence-transformers'. Install it with "
            "`pip install sentence-transformers`."
        ) from exc

    # Seed for reproducibility (affects any stochastic ops during encoding).
    import random

    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)
    try:
        import torch

        torch.manual_seed(RANDOM_SEED)
    except Exception:  # pragma: no cover - torch always present with s-t
        pass

    return SentenceTransformer(model_name, device="cpu")


class EmbeddingModel:
    """Embeds documents and queries into normalized vectors."""

    def __init__(self, model_name: str = EMBEDDING_MODEL) -> None:
        self.model_name = model_name
        self.dimension = EMBEDDING_DIM

    @property
    def model(self) -> "SentenceTransformer":
        return _load_model(self.model_name)

    def embed_texts(
        self, texts: Iterable[str], *, batch_size: int = 32
    ) -> np.ndarray:
        """Embed an iterable of texts into a ``(n, dim)`` float32 matrix with
        L2-normalized rows."""
        items = list(texts)
        if not items:
            return np.zeros((0, self.dimension), dtype=np.float32)

        vectors = self.model.encode(
            items,
            batch_size=batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.asarray(vectors, dtype=np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        """Embed a single query string into a ``(dim,)`` normalized vector."""
        vector = self.embed_texts([query])
        return vector[0]


__all__ = ["EmbeddingModel"]
