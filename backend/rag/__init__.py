"""FraudPulse RAG subsystem.

A self-contained retrieval-augmented-generation pipeline that powers the
public landing-page assistant. It answers questions strictly from a curated
corpus of FraudPulse product documentation (``rag/docs``) and refuses
anything that is not grounded in that corpus.

Pipeline:  load -> chunk -> embed -> store (FAISS) -> retrieve -> generate
(Groq) -> validate -> cite.
"""

from __future__ import annotations

__all__ = ["config"]
