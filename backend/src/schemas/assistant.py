"""Schemas for the public landing-page assistant (RAG chatbot)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AssistantSource(BaseModel):
    number: int
    title: str
    filename: str
    heading: str | None = None
    score: float


class AssistantQuery(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The visitor's question about FraudPulse.",
    )


class AssistantResponse(BaseModel):
    answer: str
    sources: list[AssistantSource] = Field(default_factory=list)
    grounded: bool = True
    refused: bool = False
    latency_ms: float = 0.0
    model: str | None = None
