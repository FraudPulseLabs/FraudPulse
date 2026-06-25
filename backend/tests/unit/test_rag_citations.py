"""Unit tests for RAG citation normalization."""

from __future__ import annotations

from rag.app.prompts import Source
from rag.app.rag_system import RagSystem, normalize_citations, to_plain_text


def _source(number: int, filename: str = "doc.md") -> Source:
    return Source(
        number=number,
        title=f"Title {number}",
        filename=filename,
        heading=f"Heading {number}",
        score=0.9,
    )


def test_renumbers_citations_sequentially():
    sources = [_source(1), _source(2), _source(3)]
    answer = "Low risk maps to ALLOW [3]. Review uses [1]."

    normalized, cited, grounded = normalize_citations(answer, sources)

    assert grounded is True
    assert normalized == "Low risk maps to ALLOW [1]. Review uses [2]."
    assert [s.number for s in cited] == [1, 2]
    assert cited[0].filename == "doc.md"
    assert cited[0].heading == "Heading 3"
    assert cited[1].heading == "Heading 1"


def test_drops_orphan_citations():
    sources = [_source(1), _source(2)]
    answer = "Valid [2] and orphan [9] citation."

    normalized, cited, grounded = normalize_citations(answer, sources)

    assert grounded is True
    assert normalized == "Valid [1] and orphan citation."
    assert len(cited) == 1
    assert cited[0].number == 1


def test_deduplicates_sources_for_repeated_citations():
    sources = [_source(1), _source(2), _source(3)]
    answer = "Same source twice [2][2] and once more [2]."

    normalized, cited, grounded = normalize_citations(answer, sources)

    assert grounded is True
    assert normalized == "Same source twice [1][1] and once more [1]."
    assert len(cited) == 1
    assert cited[0].number == 1


def test_no_valid_citations_is_not_grounded():
    sources = [_source(1), _source(2)]
    answer = "No valid refs [8][9]."

    normalized, cited, grounded = normalize_citations(answer, sources)

    assert grounded is False
    assert normalized == "No valid refs."
    assert cited == []


def test_validate_returns_normalized_answer():
    sources = [_source(1), _source(2), _source(3)]
    answer = "Details in [3] and [1]."

    grounded, cited, final = RagSystem.validate(answer, sources)

    assert grounded is True
    assert final == "Details in [1] and [2]."
    assert [s.number for s in cited] == [1, 2]


def test_to_plain_text_strips_markdown():
    raw = "**FraudPulse** uses `LightGBM` and:\n- ALLOW\n- REVIEW"

    plain = to_plain_text(raw)

    assert plain == "FraudPulse uses LightGBM and:\nALLOW\nREVIEW"
    assert "**" not in plain
    assert "`" not in plain


def test_to_plain_text_strips_links_and_numbered_lists():
    raw = "See [docs](/api) for details.\n1. ALLOW\n2. REVIEW"

    plain = to_plain_text(raw)

    assert plain == "See docs for details.\nALLOW\nREVIEW"


def test_validate_strips_markdown_and_renumbers_citations():
    sources = [_source(1), _source(2), _source(3)]
    answer = "**Risk** is scored [3]. **Decisions** include [1]."

    grounded, cited, final = RagSystem.validate(answer, sources)

    assert grounded is True
    assert final == "Risk is scored [1]. Decisions include [2]."
    assert "**" not in final
    assert [s.number for s in cited] == [1, 2]
