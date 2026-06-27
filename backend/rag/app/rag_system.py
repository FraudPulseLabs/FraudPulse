"""RAG orchestration.

Ties the pipeline together for question answering:

    retrieve (FAISS)  ->  generate (Groq)  ->  validate  ->  cite

The assistant answers strictly from the retrieved context. If the best
retrieved chunk scores below the relevance floor, the question is treated as
out-of-corpus and politely refused without ever calling the LLM.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from rag.config import (
    GROQ_API_KEY,
    GROQ_MAX_TOKENS,
    GROQ_MODEL,
    GROQ_TEMPERATURE,
    GROQ_TIMEOUT_SECONDS,
    MIN_RELEVANCE_SCORE,
    REFUSAL_MESSAGE,
    SYSTEM_PROMPT,
    TOP_K,
)
from rag.app.embeddings import EmbeddingModel
from rag.app.prompts import Source, build_sources, build_user_prompt
from rag.app.vector_store import SearchResult, VectorStore

_NO_INFO_MARKER = "i don't have information about that"
_CITATION_RE = re.compile(r"\[(\d+)\]")


def normalize_citations(
    answer: str, sources: list[Source]
) -> tuple[str, list[Source], bool]:
    """Renumber in-text citations sequentially and align the sources list.

    - Keeps only citations that reference retrieved sources (drops orphans).
    - Deduplicates sources while preserving first-appearance order in the answer.
    - Renumbers both answer markers and returned sources to 1..N with no gaps.
    """
    by_number = {s.number: s for s in sources}

    ordered_old: list[int] = []
    seen: set[int] = set()
    for raw in _CITATION_RE.findall(answer):
        num = int(raw)
        if num in by_number and num not in seen:
            seen.add(num)
            ordered_old.append(num)

    old_to_new = {old: i + 1 for i, old in enumerate(ordered_old)}

    def repl(match: re.Match[str]) -> str:
        num = int(match.group(1))
        if num in old_to_new:
            return f"[{old_to_new[num]}]"
        return ""

    normalized_answer = _CITATION_RE.sub(repl, answer)
    normalized_answer = re.sub(r"  +", " ", normalized_answer)
    normalized_answer = re.sub(r"\s+([,.;:!?])", r"\1", normalized_answer).strip()

    normalized_sources = [
        Source(
            number=old_to_new[old],
            title=by_number[old].title,
            filename=by_number[old].filename,
            heading=by_number[old].heading,
            score=by_number[old].score,
        )
        for old in ordered_old
    ]

    grounded = len(normalized_sources) > 0
    return normalized_answer, normalized_sources, grounded


def to_plain_text(answer: str) -> str:
    """Strip common Markdown markers so chat responses render as plain text."""
    text = answer
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^>\s?", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[-*]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\d+\.\s+", "", text, flags=re.MULTILINE)
    text = text.replace("**", "").replace("__", "").replace("`", "")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


@dataclass(slots=True)
class RagAnswer:
    """The result of answering a question."""

    answer: str
    sources: list[Source] = field(default_factory=list)
    grounded: bool = True
    refused: bool = False
    retrieval_scores: list[float] = field(default_factory=list)
    latency_ms: float = 0.0
    model: str = GROQ_MODEL
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "sources": [s.to_dict() for s in self.sources],
            "grounded": self.grounded,
            "refused": self.refused,
            "retrieval_scores": [round(s, 4) for s in self.retrieval_scores],
            "latency_ms": round(self.latency_ms, 1),
            "model": self.model,
            "error": self.error,
        }


class RagSystem:
    """End-to-end retrieval-augmented generation over the FraudPulse corpus."""

    def __init__(
        self,
        vector_store: VectorStore | None = None,
        embedder: EmbeddingModel | None = None,
        top_k: int = TOP_K,
        min_relevance: float = MIN_RELEVANCE_SCORE,
    ) -> None:
        self._vector_store = vector_store
        self._embedder = embedder or EmbeddingModel()
        self.top_k = top_k
        self.min_relevance = min_relevance
        self._groq_client = None

    # ------------------------------------------------------------------ #
    # Lazy resources
    # ------------------------------------------------------------------ #
    @property
    def vector_store(self) -> VectorStore:
        if self._vector_store is None:
            self._vector_store = VectorStore.load()
        return self._vector_store

    def _groq(self):
        if self._groq_client is None:
            if not GROQ_API_KEY:
                raise RuntimeError(
                    "GROQ_API_KEY is not set. Add it to backend/.env to enable "
                    "answer generation."
                )
            try:
                from groq import Groq
            except ImportError as exc:  # pragma: no cover - optional dependency
                raise RuntimeError(
                    "Answer generation requires the 'groq' package. Install it "
                    "with `pip install groq`."
                ) from exc
            self._groq_client = Groq(
                api_key=GROQ_API_KEY, timeout=GROQ_TIMEOUT_SECONDS
            )
        return self._groq_client

    # ------------------------------------------------------------------ #
    # Pipeline stages
    # ------------------------------------------------------------------ #
    def retrieve(self, question: str) -> list[SearchResult]:
        query_vec = self._embedder.embed_query(question)
        return self.vector_store.search(query_vec, top_k=self.top_k)

    def generate(self, question: str, results: list[SearchResult]) -> str:
        user_prompt = build_user_prompt(question, results)
        client = self._groq()
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=GROQ_TEMPERATURE,
            max_tokens=GROQ_MAX_TOKENS,
        )
        return (completion.choices[0].message.content or "").strip()

    @staticmethod
    def validate(answer: str, sources: list[Source]) -> tuple[bool, list[Source], str]:
        """Check grounding and return sequential citations aligned to sources."""
        cleaned = to_plain_text(answer)
        lowered = cleaned.lower()
        if _NO_INFO_MARKER in lowered:
            return False, [], cleaned

        normalized_answer, normalized_sources, grounded = normalize_citations(
            cleaned, sources
        )
        return grounded, normalized_sources, to_plain_text(normalized_answer)

    # ------------------------------------------------------------------ #
    # Public entry point
    # ------------------------------------------------------------------ #
    def answer(self, question: str) -> RagAnswer:
        start = time.perf_counter()
        question = (question or "").strip()

        if not question:
            return RagAnswer(
                answer="Please ask a question about FraudPulse.",
                refused=True,
                grounded=False,
                latency_ms=(time.perf_counter() - start) * 1000,
            )

        results = self.retrieve(question)
        scores = [r.score for r in results]

        # Refuse out-of-corpus questions before spending an LLM call.
        if not results or results[0].score < self.min_relevance:
            return RagAnswer(
                answer=REFUSAL_MESSAGE,
                refused=True,
                grounded=False,
                retrieval_scores=scores,
                latency_ms=(time.perf_counter() - start) * 1000,
            )

        sources = build_sources(results)

        try:
            raw_answer = self.generate(question, results)
        except RuntimeError as exc:
            return RagAnswer(
                answer=(
                    "The assistant is temporarily unavailable. Please try again "
                    "later or use the Request access form to reach the team."
                ),
                sources=[],
                grounded=False,
                refused=False,
                retrieval_scores=scores,
                latency_ms=(time.perf_counter() - start) * 1000,
                error=str(exc),
            )

        grounded, cited_sources, final_answer = self.validate(raw_answer, sources)
        refused = _NO_INFO_MARKER in raw_answer.lower()

        return RagAnswer(
            answer=final_answer,
            sources=[] if refused else cited_sources,
            grounded=grounded,
            refused=refused,
            retrieval_scores=scores,
            latency_ms=(time.perf_counter() - start) * 1000,
        )


@lru_cache(maxsize=1)
def get_rag_system() -> RagSystem:
    """Process-wide singleton so the index and embedding model load once."""
    return RagSystem()


__all__ = ["RagSystem", "RagAnswer", "get_rag_system", "normalize_citations", "to_plain_text"]
