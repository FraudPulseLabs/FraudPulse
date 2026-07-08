"""Chunking.

Splits :class:`Document` objects into :class:`Chunk` objects using a hybrid
strategy:

1. **Heading-aware split** — Markdown documents are first split on headings
   (``#``..``######``) so each section stays semantically coherent and carries
   its heading as context.
2. **Sliding-window fallback** — any section longer than ``CHUNK_SIZE`` is
   further split with a character sliding window of size ``CHUNK_SIZE`` and
   ``CHUNK_OVERLAP`` overlap, breaking on sentence/word boundaries where
   possible.

The process is fully deterministic (seeded) so the same corpus always produces
the same chunks in the same order.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from typing import Any

from rag.config import CHUNK_OVERLAP, CHUNK_SIZE, RANDOM_SEED
from rag.app.document_loader import Document

# Seed module-level RNG for determinism. No randomness is required by the
# algorithm itself, but seeding guarantees reproducibility if it is ever added.
random.seed(RANDOM_SEED)

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)


@dataclass(slots=True)
class Chunk:
    """A retrievable unit of text with provenance metadata."""

    chunk_id: str
    doc_id: str
    title: str
    filename: str
    text: str
    heading: str | None = None
    chunk_index: int = 0
    word_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.word_count:
            self.word_count = len(self.text.split())

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "title": self.title,
            "filename": self.filename,
            "text": self.text,
            "heading": self.heading,
            "chunk_index": self.chunk_index,
            "word_count": self.word_count,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Chunk":
        return cls(
            chunk_id=data["chunk_id"],
            doc_id=data["doc_id"],
            title=data["title"],
            filename=data["filename"],
            text=data["text"],
            heading=data.get("heading"),
            chunk_index=data.get("chunk_index", 0),
            word_count=data.get("word_count", 0),
            metadata=data.get("metadata", {}),
        )


# --------------------------------------------------------------------------- #
# Heading-aware splitting
# --------------------------------------------------------------------------- #
@dataclass(slots=True)
class _Section:
    heading: str | None
    text: str


def _split_into_sections(text: str) -> list[_Section]:
    """Split a Markdown document into (heading, body) sections.

    Text before the first heading becomes a section with no heading.
    """
    matches = list(_HEADING_RE.finditer(text))
    if not matches:
        return [_Section(heading=None, text=text.strip())]

    sections: list[_Section] = []

    preamble = text[: matches[0].start()].strip()
    if preamble:
        sections.append(_Section(heading=None, text=preamble))

    for i, match in enumerate(matches):
        heading_text = match.group(2).strip()
        body_start = match.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip()
        # Keep the heading line as part of the section text for context.
        section_text = f"{match.group(0).strip()}\n{body}".strip()
        sections.append(_Section(heading=heading_text, text=section_text))

    return [s for s in sections if s.text]


# --------------------------------------------------------------------------- #
# Sliding-window splitting
# --------------------------------------------------------------------------- #
def _sliding_window(
    text: str, chunk_size: int, overlap: int
) -> list[str]:
    """Split text into overlapping windows, preferring to break on sentence or
    word boundaries near the window edge."""
    text = text.strip()
    if len(text) <= chunk_size:
        return [text] if text else []

    step = max(1, chunk_size - overlap)
    windows: list[str] = []
    start = 0
    n = len(text)

    while start < n:
        end = min(start + chunk_size, n)
        if end < n:
            # Try to end on a sentence boundary, then a newline, then a space.
            window = text[start:end]
            for boundary in (". ", ".\n", "\n\n", "\n", " "):
                idx = window.rfind(boundary)
                # Only honour the boundary if it keeps a reasonable chunk size.
                if idx != -1 and idx >= int(chunk_size * 0.5):
                    end = start + idx + len(boundary)
                    break
        piece = text[start:end].strip()
        if piece:
            windows.append(piece)
        if end >= n:
            break
        start = max(start + step, end - overlap)

    return windows


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def chunk_document(
    document: Document,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[Chunk]:
    """Chunk a single document with the hybrid heading + sliding-window strategy."""
    chunks: list[Chunk] = []
    index = 0

    for section in _split_into_sections(document.text):
        if len(section.text) <= chunk_size:
            pieces = [section.text]
        else:
            pieces = _sliding_window(section.text, chunk_size, chunk_overlap)

        for piece in pieces:
            piece = piece.strip()
            if not piece:
                continue
            chunks.append(
                Chunk(
                    chunk_id=f"{document.doc_id}::{index}",
                    doc_id=document.doc_id,
                    title=document.title,
                    filename=document.filename,
                    text=piece,
                    heading=section.heading,
                    chunk_index=index,
                    metadata={"source_path": document.metadata.get("source_path")},
                )
            )
            index += 1

    return chunks


def chunk_documents(
    documents: list[Document],
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[Chunk]:
    """Chunk a list of documents, preserving document order for determinism."""
    all_chunks: list[Chunk] = []
    for document in documents:
        all_chunks.extend(chunk_document(document, chunk_size, chunk_overlap))
    return all_chunks


__all__ = ["Chunk", "chunk_document", "chunk_documents"]
