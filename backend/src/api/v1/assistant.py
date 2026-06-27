"""
POST /api/v1/assistant/chat

Public endpoint that powers the landing-page assistant. It forwards the
visitor's question to the RAG pipeline (``rag/``), which retrieves relevant
passages from the FraudPulse documentation corpus and generates a grounded,
cited answer with a Groq-hosted LLM. Questions outside the corpus are refused.

The endpoint is defined synchronously so FastAPI runs the CPU-bound embedding
and the blocking LLM call in its worker threadpool.
"""

import logging

from fastapi import APIRouter, HTTPException, Request

from src.core.rate_limit import LIMIT_ASSISTANT, limiter
from src.schemas.assistant import AssistantQuery, AssistantResponse, AssistantSource

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat", response_model=AssistantResponse)
@limiter.limit(LIMIT_ASSISTANT)
def assistant_chat(request: Request, payload: AssistantQuery) -> AssistantResponse:
    try:
        # Imported lazily so the API can boot even if the RAG extras
        # (faiss / sentence-transformers) or the built index are unavailable.
        from rag.app.rag_system import get_rag_system

        rag = get_rag_system()
        result = rag.answer(payload.message)
    except FileNotFoundError as exc:
        logger.error("RAG index not built: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=(
                "The assistant is not ready yet. Build the index with "
                "`python -m rag.scripts.build_vector_db`."
            ),
        ) from exc
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Assistant failed to answer")
        raise HTTPException(
            status_code=503, detail="The assistant is temporarily unavailable."
        ) from exc

    return AssistantResponse(
        answer=result.answer,
        sources=[AssistantSource(**s.to_dict()) for s in result.sources],
        grounded=result.grounded,
        refused=result.refused,
        latency_ms=round(result.latency_ms, 1),
        model=result.model,
    )
