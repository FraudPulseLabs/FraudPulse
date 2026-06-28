"""Document loader.

Loads the corpus from ``rag/docs`` into clean :class:`Document` objects with
useful metadata (title, filename, word count). Supports Markdown (.md), plain
text (.txt), HTML (.html/.htm), and PDF (.pdf).

The loader is deterministic: files are processed in sorted order so a rebuild
always yields the same document order.
"""

from __future__ import annotations

import html as html_module
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rag.config import DOCS_DIR

SUPPORTED_SUFFIXES = {".md", ".markdown", ".txt", ".html", ".htm", ".pdf"}


@dataclass(slots=True)
class Document:
    """A single cleaned source document."""

    doc_id: str
    title: str
    filename: str
    text: str
    word_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.word_count:
            self.word_count = len(self.text.split())

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "filename": self.filename,
            "text": self.text,
            "word_count": self.word_count,
            "metadata": self.metadata,
        }


# --------------------------------------------------------------------------- #
# Cleaning helpers
# --------------------------------------------------------------------------- #
def _normalise_whitespace(text: str) -> str:
    """Collapse excessive blank lines and trailing spaces while preserving
    paragraph and heading structure (important for the heading-aware chunker)."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Strip trailing spaces on each line.
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)
    # Collapse 3+ blank lines into a single blank line.
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _strip_html(raw: str) -> str:
    """Very small HTML-to-text conversion that keeps headings as Markdown."""
    # Drop script/style blocks entirely.
    raw = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", "", raw)
    # Convert heading tags to Markdown headings so the chunker can use them.
    for level in range(1, 7):
        raw = re.sub(
            rf"(?is)<h{level}[^>]*>(.*?)</h{level}>",
            lambda m, lvl=level: f"\n\n{'#' * lvl} {m.group(1).strip()}\n\n",
            raw,
        )
    # Paragraph and line breaks -> newlines.
    raw = re.sub(r"(?is)</p\s*>", "\n\n", raw)
    raw = re.sub(r"(?is)<br\s*/?>", "\n", raw)
    # Remove any remaining tags.
    raw = re.sub(r"(?s)<[^>]+>", "", raw)
    # Unescape entities (&amp; -> &).
    raw = html_module.unescape(raw)
    return raw


def _read_pdf(path: Path) -> str:
    """Extract text from a PDF. Requires ``pypdf`` to be installed."""
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "Reading PDF documents requires the 'pypdf' package. "
            "Install it with `pip install pypdf`."
        ) from exc

    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages)


def _derive_title(text: str, fallback: str) -> str:
    """Use the first Markdown H1, else the first non-empty line, else filename."""
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
        if stripped and not stripped.startswith("#"):
            return stripped[:120]
    return fallback


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def load_file(path: Path) -> Document | None:
    """Load and clean a single file into a :class:`Document` (or ``None`` if
    the file type is unsupported or the cleaned text is empty)."""
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        return None

    if suffix == ".pdf":
        raw = _read_pdf(path)
    else:
        raw = path.read_text(encoding="utf-8", errors="replace")
        if suffix in {".html", ".htm"}:
            raw = _strip_html(raw)

    text = _normalise_whitespace(raw)
    if not text:
        return None

    title = _derive_title(text, fallback=path.stem.replace("-", " ").title())
    return Document(
        doc_id=path.stem,
        title=title,
        filename=path.name,
        text=text,
        metadata={
            "source_path": str(path),
            "suffix": suffix,
        },
    )


def load_documents(docs_dir: Path | None = None) -> list[Document]:
    """Load every supported document in ``docs_dir`` (defaults to ``rag/docs``).

    Files are processed in sorted order for deterministic output.
    """
    directory = Path(docs_dir) if docs_dir is not None else DOCS_DIR
    if not directory.exists():
        raise FileNotFoundError(f"Corpus directory not found: {directory}")

    documents: list[Document] = []
    for path in sorted(directory.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        doc = load_file(path)
        if doc is not None:
            documents.append(doc)

    if not documents:
        raise ValueError(
            f"No supported documents found in {directory}. "
            f"Supported types: {sorted(SUPPORTED_SUFFIXES)}"
        )
    return documents


__all__ = ["Document", "load_file", "load_documents", "SUPPORTED_SUFFIXES"]
