"""Prompt assembly.

Turns retrieved chunks into a numbered CONTEXT block and builds the final user
message sent to the LLM. The system prompt itself lives in ``rag.config`` so
all behavioural settings are configured in one place.
"""

from __future__ import annotations

from dataclasses import dataclass

from rag.app.vector_store import SearchResult


@dataclass(slots=True)
class Source:
    """A citation source surfaced alongside an answer."""

    number: int
    title: str
    filename: str
    heading: str | None
    score: float

    def to_dict(self) -> dict:
        return {
            "number": self.number,
            "title": self.title,
            "filename": self.filename,
            "heading": self.heading,
            "score": round(self.score, 4),
        }


def build_sources(results: list[SearchResult]) -> list[Source]:
    """Map ranked search results to numbered citation sources (1-indexed)."""
    return [
        Source(
            number=i + 1,
            title=r.chunk.title,
            filename=r.chunk.filename,
            heading=r.chunk.heading,
            score=r.score,
        )
        for i, r in enumerate(results)
    ]


def format_context(results: list[SearchResult]) -> str:
    """Render retrieved chunks into a numbered context block for the prompt."""
    blocks: list[str] = []
    for i, result in enumerate(results):
        chunk = result.chunk
        location = chunk.title
        if chunk.heading:
            location += f" — {chunk.heading}"
        blocks.append(
            f"[{i + 1}] (source: {location})\n{chunk.text.strip()}"
        )
    return "\n\n".join(blocks)


def build_user_prompt(question: str, results: list[SearchResult]) -> str:
    """Assemble the final user message: context + question + citation reminder."""
    context = format_context(results)
    return (
        "Answer the question using ONLY the context below. Cite the sources you "
        "use with bracketed numbers like [1] or [2][3]. If the context does not "
        "contain the answer, say you don't have information about that in the "
        "FraudPulse documentation.\n\n"
        f"CONTEXT:\n{context}\n\n"
        f"QUESTION: {question.strip()}\n\n"
        "ANSWER:"
    )


__all__ = ["Source", "build_sources", "format_context", "build_user_prompt"]
