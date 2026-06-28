"""Evaluation.

Measures the RAG assistant on three axes:

* **Groundedness** — does an in-corpus answer stay anchored to retrieved
  context (cites at least one valid source and does not refuse spuriously)?
* **Citation accuracy** — does the answer cite the document the question is
  expected to come from?
* **Latency** — end-to-end answer time per query (mean / p50 / p95).

It also checks **refusal accuracy**: out-of-corpus questions must be refused.

The evaluation uses the same :class:`RagSystem` used in production, so results
reflect the real retrieve -> generate -> validate -> cite pipeline.
"""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rag.config import EVAL_DIR
from rag.app.rag_system import RagAnswer, RagSystem, get_rag_system

QA_PATH = EVAL_DIR / "qa_pairs.json"
RESULTS_PATH = EVAL_DIR / "results.json"


@dataclass(slots=True)
class CaseResult:
    question: str
    answer: str
    grounded: bool
    refused: bool
    cited_sources: list[str]
    keyword_hits: float
    citation_correct: bool | None
    latency_ms: float
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "answer": self.answer,
            "grounded": self.grounded,
            "refused": self.refused,
            "cited_sources": self.cited_sources,
            "keyword_hits": round(self.keyword_hits, 3),
            "citation_correct": self.citation_correct,
            "latency_ms": round(self.latency_ms, 1),
            "error": self.error,
        }


@dataclass(slots=True)
class EvaluationReport:
    in_corpus: list[CaseResult] = field(default_factory=list)
    out_of_corpus: list[CaseResult] = field(default_factory=list)

    # ---- aggregate metrics ---- #
    def _latencies(self) -> list[float]:
        return [c.latency_ms for c in self.in_corpus + self.out_of_corpus]

    def metrics(self) -> dict[str, Any]:
        in_corpus = self.in_corpus
        n = len(in_corpus) or 1

        groundedness = sum(1 for c in in_corpus if c.grounded) / n
        keyword_recall = sum(c.keyword_hits for c in in_corpus) / n
        cited = [c for c in in_corpus if c.citation_correct is not None]
        citation_accuracy = (
            sum(1 for c in cited if c.citation_correct) / len(cited)
            if cited
            else None
        )
        # In-corpus questions should NOT be refused.
        false_refusals = sum(1 for c in in_corpus if c.refused) / n

        ooc = self.out_of_corpus
        m = len(ooc) or 1
        refusal_accuracy = sum(1 for c in ooc if c.refused) / m

        latencies = self._latencies() or [0.0]
        latencies_sorted = sorted(latencies)
        p95_idx = max(0, int(round(0.95 * (len(latencies_sorted) - 1))))

        return {
            "groundedness": round(groundedness, 3),
            "citation_accuracy": (
                round(citation_accuracy, 3)
                if citation_accuracy is not None
                else None
            ),
            "keyword_recall": round(keyword_recall, 3),
            "false_refusal_rate": round(false_refusals, 3),
            "out_of_corpus_refusal_accuracy": round(refusal_accuracy, 3),
            "latency_ms": {
                "mean": round(statistics.fmean(latencies), 1),
                "p50": round(statistics.median(latencies_sorted), 1),
                "p95": round(latencies_sorted[p95_idx], 1),
                "max": round(max(latencies_sorted), 1),
            },
            "counts": {
                "in_corpus": len(in_corpus),
                "out_of_corpus": len(ooc),
            },
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "metrics": self.metrics(),
            "in_corpus": [c.to_dict() for c in self.in_corpus],
            "out_of_corpus": [c.to_dict() for c in self.out_of_corpus],
        }


# --------------------------------------------------------------------------- #
# Scoring helpers
# --------------------------------------------------------------------------- #
def _keyword_hits(answer: str, keywords: list[str]) -> float:
    if not keywords:
        return 1.0
    lowered = answer.lower()
    hits = sum(1 for kw in keywords if kw.lower() in lowered)
    return hits / len(keywords)


def _citation_correct(result: RagAnswer, expected_source: str | None) -> bool | None:
    if not expected_source:
        return None
    return any(s.filename == expected_source for s in result.sources)


def _evaluate_case(
    rag: RagSystem, item: dict[str, Any], *, in_corpus: bool
) -> CaseResult:
    question = item["question"]
    result = rag.answer(question)

    keyword_hits = (
        _keyword_hits(result.answer, item.get("expected_keywords", []))
        if in_corpus
        else 0.0
    )
    citation_correct = (
        _citation_correct(result, item.get("expected_source"))
        if in_corpus
        else None
    )

    return CaseResult(
        question=question,
        answer=result.answer,
        grounded=result.grounded,
        refused=result.refused,
        cited_sources=[s.filename for s in result.sources],
        keyword_hits=keyword_hits,
        citation_correct=citation_correct,
        latency_ms=result.latency_ms,
        error=result.error,
    )


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def load_qa_pairs(path: Path = QA_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate(
    rag: RagSystem | None = None, qa_path: Path = QA_PATH
) -> EvaluationReport:
    """Run the full evaluation suite and return a report."""
    rag = rag or get_rag_system()
    qa = load_qa_pairs(qa_path)
    report = EvaluationReport()

    for item in qa.get("in_corpus", []):
        report.in_corpus.append(_evaluate_case(rag, item, in_corpus=True))
    for item in qa.get("out_of_corpus", []):
        report.out_of_corpus.append(_evaluate_case(rag, item, in_corpus=False))

    return report


def save_report(report: EvaluationReport, path: Path = RESULTS_PATH) -> None:
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")


__all__ = [
    "CaseResult",
    "EvaluationReport",
    "evaluate",
    "load_qa_pairs",
    "save_report",
    "QA_PATH",
    "RESULTS_PATH",
]
