"""Evaluate the FraudPulse RAG assistant.

Runs the evaluation suite (groundedness, citation accuracy, latency, and
out-of-corpus refusal accuracy) and writes a JSON report.

Run from the ``backend/`` directory:

    python -m rag.scripts.evaluate

Requires a built index (``python -m rag.scripts.build_vector_db``) and, for
generation, ``GROQ_API_KEY`` in ``backend/.env``.
"""

from __future__ import annotations

import argparse
import json
import sys

from rag.config import GROQ_API_KEY
from rag.app.evaluation import RESULTS_PATH, evaluate, save_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the RAG assistant.")
    parser.add_argument(
        "--json", action="store_true", help="Print the full report as JSON."
    )
    args = parser.parse_args()

    if not GROQ_API_KEY:
        print(
            "WARNING: GROQ_API_KEY is not set. Generation will fail and answers "
            "will be marked unavailable. Set it in backend/.env for a full "
            "evaluation.\n",
            file=sys.stderr,
        )

    report = evaluate()
    save_report(report)
    metrics = report.metrics()

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
        return

    print("=" * 60)
    print("FraudPulse RAG — Evaluation Report")
    print("=" * 60)
    print(f"In-corpus questions     : {metrics['counts']['in_corpus']}")
    print(f"Out-of-corpus questions : {metrics['counts']['out_of_corpus']}")
    print("-" * 60)
    print(f"Groundedness            : {metrics['groundedness']:.1%}")
    citation = metrics["citation_accuracy"]
    print(
        "Citation accuracy       : "
        + (f"{citation:.1%}" if citation is not None else "n/a")
    )
    print(f"Keyword recall          : {metrics['keyword_recall']:.1%}")
    print(f"False refusal rate      : {metrics['false_refusal_rate']:.1%}")
    print(
        f"OOC refusal accuracy    : "
        f"{metrics['out_of_corpus_refusal_accuracy']:.1%}"
    )
    print("-" * 60)
    lat = metrics["latency_ms"]
    print(
        f"Latency (ms)            : mean={lat['mean']} p50={lat['p50']} "
        f"p95={lat['p95']} max={lat['max']}"
    )
    print("=" * 60)
    print(f"Full report written to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
