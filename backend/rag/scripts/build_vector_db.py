"""Build the FraudPulse RAG vector database.

Runs the offline indexing pipeline end to end:

    load (docs)  ->  chunk  ->  embed  ->  save (FAISS index + sidecar)

Run from the ``backend/`` directory:

    python -m rag.scripts.build_vector_db

The result is written to ``rag/index/`` and is read at query time by the
assistant.
"""

from __future__ import annotations

import argparse
import time

from rag.config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    DOCS_DIR,
    EMBEDDING_MODEL,
    INDEX_DIR,
)
from rag.app.chunking import chunk_documents
from rag.app.document_loader import load_documents
from rag.app.embeddings import EmbeddingModel
from rag.app.vector_store import VectorStore


def build() -> None:
    overall_start = time.perf_counter()

    print(f"[1/4] Loading documents from {DOCS_DIR} ...")
    documents = load_documents()
    total_words = sum(d.word_count for d in documents)
    print(f"      Loaded {len(documents)} documents ({total_words:,} words).")
    for doc in documents:
        print(f"        - {doc.filename}: {doc.word_count:,} words")

    print(
        f"[2/4] Chunking (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP}, "
        "hybrid heading + sliding-window) ..."
    )
    chunks = chunk_documents(documents)
    print(f"      Produced {len(chunks)} chunks.")

    print(f"[3/4] Embedding chunks with {EMBEDDING_MODEL} ...")
    embed_start = time.perf_counter()
    embedder = EmbeddingModel()
    embeddings = embedder.embed_texts(c.text for c in chunks)
    print(
        f"      Embedded {embeddings.shape[0]} chunks "
        f"(dim={embeddings.shape[1]}) in "
        f"{time.perf_counter() - embed_start:.1f}s."
    )

    print(f"[4/4] Building FAISS IndexFlatIP and saving to {INDEX_DIR} ...")
    store = VectorStore(dimension=embeddings.shape[1])
    store.add(chunks, embeddings)
    store.save()

    print(
        f"\nDone. Indexed {store.size} chunks in "
        f"{time.perf_counter() - overall_start:.1f}s.\n"
        f"Artefacts written to {INDEX_DIR}."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the RAG vector database.")
    parser.parse_args()
    build()


if __name__ == "__main__":
    main()
