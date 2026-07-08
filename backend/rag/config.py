"""Central configuration for the FraudPulse RAG subsystem.

Everything tunable lives here: filesystem paths, the deterministic random
seed, model identifiers, chunking parameters, retrieval depth, and the system
prompt that constrains the assistant to the corpus.

Secrets (the Groq API key) are read from the environment, never hard-coded.
Copy ``backend/.env.example`` to ``backend/.env`` and set ``GROQ_API_KEY``.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
RAG_DIR: Path = Path(__file__).resolve().parent          # backend/rag
BACKEND_DIR: Path = RAG_DIR.parent                        # backend
PROJECT_ROOT: Path = BACKEND_DIR.parent                  # repo root

DOCS_DIR: Path = RAG_DIR / "docs"                         # source corpus
INDEX_DIR: Path = RAG_DIR / "index"                       # built vector store
EVAL_DIR: Path = RAG_DIR / "eval"                         # evaluation fixtures

# Persisted vector-store artefacts.
FAISS_INDEX_PATH: Path = INDEX_DIR / "faiss.index"
CHUNKS_PATH: Path = INDEX_DIR / "chunks.json"
INDEX_META_PATH: Path = INDEX_DIR / "meta.json"

# Load backend/.env so GROQ_API_KEY (and friends) are available.
load_dotenv(BACKEND_DIR / ".env")

# --------------------------------------------------------------------------- #
# Determinism
# --------------------------------------------------------------------------- #
RANDOM_SEED: int = 42

# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #
# Generation — Groq-hosted LLM. Override with GROQ_MODEL if desired.
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_API_KEY: str | None = os.getenv("GROQ_API_KEY")
GROQ_TIMEOUT_SECONDS: float = float(os.getenv("GROQ_TIMEOUT_SECONDS", "30"))
# Low temperature keeps answers faithful to the retrieved context.
GROQ_TEMPERATURE: float = float(os.getenv("GROQ_TEMPERATURE", "0.1"))
GROQ_MAX_TOKENS: int = int(os.getenv("GROQ_MAX_TOKENS", "700"))

# Embeddings — local sentence-transformers model (no network at query time).
EMBEDDING_MODEL: str = os.getenv(
    "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)
EMBEDDING_DIM: int = 384  # all-MiniLM-L6-v2 output dimensionality

# --------------------------------------------------------------------------- #
# Chunking
# --------------------------------------------------------------------------- #
CHUNK_SIZE: int = 1000      # target characters per chunk
CHUNK_OVERLAP: int = 200    # sliding-window overlap (characters)

# --------------------------------------------------------------------------- #
# Retrieval
# --------------------------------------------------------------------------- #
TOP_K: int = 5
# Minimum cosine similarity for a chunk to count as relevant. Queries whose
# best match falls below this are treated as out-of-corpus and refused.
MIN_RELEVANCE_SCORE: float = 0.25

# --------------------------------------------------------------------------- #
# Prompting
# --------------------------------------------------------------------------- #
REFUSAL_MESSAGE: str = (
    "I can only answer questions about FraudPulse using its documentation, and "
    "I couldn't find anything relevant to that. Try asking about how scoring "
    "works, the allow/review/block decisions, the API, the tech stack, "
    "security and compliance, or how to request access."
)

SYSTEM_PROMPT: str = """\
You are the FraudPulse Assistant, a precise product expert for FraudPulse — a \
real-time payment fraud detection platform.

Follow these rules without exception:
1. Answer ONLY using the information in the provided CONTEXT. The context is the \
   single source of truth.
2. If the context does not contain the answer, reply with exactly: \
   "I don't have information about that in the FraudPulse documentation." Do not \
   guess, infer beyond the context, or use outside knowledge.
3. Never invent product features, numbers, endpoints, prices, or guarantees \
   that are not stated in the context.
4. Cite the sources you used. After the relevant sentence(s), add bracketed \
   citations that reference the numbered sources, e.g. [1] or [2][3].
5. Be concise, professional, and helpful. Write in plain text only: no Markdown, \
   no bold/italic markers, no headings, and no bullet syntax. Use short paragraphs \
   or simple numbered lines when listing items.
6. If the user is conversational (greetings, thanks), respond briefly and \
   invite a FraudPulse question.
"""

__all__ = [
    "RAG_DIR",
    "BACKEND_DIR",
    "PROJECT_ROOT",
    "DOCS_DIR",
    "INDEX_DIR",
    "EVAL_DIR",
    "FAISS_INDEX_PATH",
    "CHUNKS_PATH",
    "INDEX_META_PATH",
    "RANDOM_SEED",
    "GROQ_MODEL",
    "GROQ_API_KEY",
    "GROQ_TIMEOUT_SECONDS",
    "GROQ_TEMPERATURE",
    "GROQ_MAX_TOKENS",
    "EMBEDDING_MODEL",
    "EMBEDDING_DIM",
    "CHUNK_SIZE",
    "CHUNK_OVERLAP",
    "TOP_K",
    "MIN_RELEVANCE_SCORE",
    "REFUSAL_MESSAGE",
    "SYSTEM_PROMPT",
]
