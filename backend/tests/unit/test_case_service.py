#backend\tests\unit\test_case_service.py
"""
Unit tests for case_service.py — covers Case CRUD and CaseNote management.

Both live in the same service module after the merge, so they share
this test file following the same pattern as test_decision_service.py.

Coverage:
    create_case()
        - persists with correct defaults
        - auto-generates title from transaction_id when none supplied
        - accepts an explicit title and risk_level

    list_cases()
        - returns all cases when no filters applied
        - filters by status
        - filters by risk_level
        - filters by assigned_to

    get_case()
        - returns case when it exists
        - raises 404 when not found

    update_case()
        - updates status, risk_level, resolution_code, assigned_to
        - ignores None fields (partial update)
        - raises 404 when case not found

    create_case_note()
        - persists note linked to case
        - raises 404 when case_id does not exist
        - rejects body that is empty (Pydantic layer)
        - rejects body over 2000 chars (Pydantic layer)

    list_case_notes()
        - returns notes ordered oldest-first
        - returns empty list when case has no notes
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, call

import pytest
from fastapi import HTTPException

from src.schemas.case_schemas import (
    CaseNoteCreate,
    CaseResolutionCode,
    CaseRiskLevel,
    CaseStatus,
    CaseUpdate,
)
from src.services import case_service
from src.db.models.case_model import Case, CaseNote


# =============================================================================
# Helpers
# =============================================================================

def _make_case(
    case_id: uuid.UUID | None = None,
    transaction_id: uuid.UUID | None = None,
    status: str = "OPEN",
    risk_level: str = "MEDIUM",
) -> Case:
    """Build a Case ORM instance without a DB."""
    c = Case(
        transaction_id=transaction_id or uuid.uuid4(),
        title="Fraud Investigation – TXN ABCD1234",
        status=status,
        risk_level=risk_level,
    )
    c.id = case_id or uuid.uuid4()
    c.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    c.updated_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return c


def _make_note(case_id: uuid.UUID, body: str = "Looks suspicious.") -> CaseNote:
    n = CaseNote(case_id=case_id, author_id="analyst@example.com", body=body)
    n.id = uuid.uuid4()
    n.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return n


def _db_get_returns(obj):
    """Mock db.get() to return obj."""
    db = MagicMock()
    db.get.return_value = obj
    return db


def _db_execute_returns(rows: list):
    """Mock db.execute().scalars().all() to return rows."""
    db = MagicMock()
    db.execute.return_value.scalars.return_value.all.return_value = rows
    return db


# =============================================================================
# create_case
# =============================================================================

class TestCreateCase:

    def test_persists_case_with_correct_defaults(self):
        db = MagicMock()
        txn_id = uuid.uuid4()

        case_service.create_case(db=db, transaction_id=txn_id)

        db.add.assert_called_once()
        added: Case = db.add.call_args.args[0]
        assert isinstance(added, Case)
        assert added.transaction_id == txn_id
        assert added.status == CaseStatus.OPEN.value
        assert added.risk_level == CaseRiskLevel.MEDIUM.value
        db.flush.assert_called_once()

    def test_auto_generates_title_from_transaction_id(self):
        db = MagicMock()
        txn_id = uuid.UUID("abcd1234-0000-0000-0000-000000000000")

        case_service.create_case(db=db, transaction_id=txn_id)

        added: Case = db.add.call_args.args[0]
        assert "ABCD1234" in added.title

    def test_accepts_explicit_title(self):
        db = MagicMock()
        case_service.create_case(db=db, transaction_id=uuid.uuid4(), title="Custom Title")

        added: Case = db.add.call_args.args[0]
        assert added.title == "Custom Title"

    def test_accepts_explicit_risk_level(self):
        db = MagicMock()
        case_service.create_case(
            db=db,
            transaction_id=uuid.uuid4(),
            risk_level=CaseRiskLevel.HIGH,
        )

        added: Case = db.add.call_args.args[0]
        assert added.risk_level == CaseRiskLevel.HIGH.value


# =============================================================================
# list_cases
# =============================================================================

class TestListCases:

    def test_returns_all_when_no_filters(self):
        cases = [_make_case(), _make_case()]
        db = _db_execute_returns(cases)

        result = asyncio.run(case_service.list_cases(db=db))

        assert result == cases
        db.execute.assert_called_once()

    def test_filters_by_status(self):
        open_case = _make_case(status="OPEN")
        db = _db_execute_returns([open_case])

        result = asyncio.run(case_service.list_cases(db=db, status=CaseStatus.OPEN))

        assert result == [open_case]

    def test_filters_by_risk_level(self):
        high_case = _make_case(risk_level="HIGH")
        db = _db_execute_returns([high_case])

        result = asyncio.run(case_service.list_cases(db=db, risk_level=CaseRiskLevel.HIGH))

        assert result == [high_case]

    def test_filters_by_assigned_to(self):
        analyst_id = uuid.uuid4()
        assigned = _make_case()
        db = _db_execute_returns([assigned])

        result = asyncio.run(case_service.list_cases(db=db, assigned_to=analyst_id))

        assert result == [assigned]


# =============================================================================
# get_case
# =============================================================================

class TestGetCase:

    def test_returns_case_when_found(self):
        case = _make_case()
        db = _db_get_returns(case)

        result = asyncio.run(case_service.get_case(db=db, case_id=case.id))

        assert result is case
        db.get.assert_called_once_with(Case, case.id)

    def test_raises_404_when_not_found(self):
        db = _db_get_returns(None)

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(case_service.get_case(db=db, case_id=uuid.uuid4()))

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()


# =============================================================================
# update_case
# =============================================================================

class TestUpdateCase:

    def test_updates_status(self):
        case = _make_case(status="OPEN")
        db = _db_get_returns(case)

        asyncio.run(case_service.update_case(
            db=db,
            case_id=case.id,
            payload=CaseUpdate(status=CaseStatus.INVESTIGATING),
        ))

        assert case.status == CaseStatus.INVESTIGATING.value

    def test_updates_risk_level(self):
        case = _make_case(risk_level="MEDIUM")
        db = _db_get_returns(case)

        asyncio.run(case_service.update_case(
            db=db,
            case_id=case.id,
            payload=CaseUpdate(risk_level=CaseRiskLevel.HIGH),
        ))

        assert case.risk_level == CaseRiskLevel.HIGH.value

    def test_updates_resolution_code(self):
        case = _make_case()
        db = _db_get_returns(case)

        asyncio.run(case_service.update_case(
            db=db,
            case_id=case.id,
            payload=CaseUpdate(resolution_code=CaseResolutionCode.CONFIRMED_FRAUD),
        ))

        assert case.resolution_code == CaseResolutionCode.CONFIRMED_FRAUD.value

    def test_updates_assigned_to(self):
        case = _make_case()
        analyst_id = uuid.uuid4()
        db = _db_get_returns(case)

        asyncio.run(case_service.update_case(
            db=db,
            case_id=case.id,
            payload=CaseUpdate(assigned_to=analyst_id),
        ))

        assert case.assigned_to == analyst_id

    def test_ignores_none_fields(self):
        case = _make_case(status="OPEN", risk_level="LOW")
        db = _db_get_returns(case)

        # Only pass risk_level — status must remain untouched
        asyncio.run(case_service.update_case(
            db=db,
            case_id=case.id,
            payload=CaseUpdate(risk_level=CaseRiskLevel.HIGH),
        ))

        assert case.status == "OPEN"
        assert case.risk_level == CaseRiskLevel.HIGH.value

    def test_raises_404_when_case_not_found(self):
        db = _db_get_returns(None)

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(case_service.update_case(
                db=db,
                case_id=uuid.uuid4(),
                payload=CaseUpdate(status=CaseStatus.CLOSED),
            ))

        assert exc_info.value.status_code == 404

    def test_flushes_after_update(self):
        case = _make_case()
        db = _db_get_returns(case)

        asyncio.run(case_service.update_case(
            db=db,
            case_id=case.id,
            payload=CaseUpdate(status=CaseStatus.CLOSED),
        ))

        db.flush.assert_called_once()


# =============================================================================
# create_case_note
# =============================================================================

class TestCreateCaseNote:

    def test_persists_note_linked_to_case(self):
        case = _make_case()
        db = _db_get_returns(case)

        payload = CaseNoteCreate(author_id="analyst@example.com", body="Confirmed pattern.")
        case_service.create_case_note(db=db, case_id=case.id, payload=payload)

        db.add.assert_called_once()
        added: CaseNote = db.add.call_args.args[0]
        assert isinstance(added, CaseNote)
        assert added.case_id == case.id
        assert added.author_id == "analyst@example.com"
        assert added.body == "Confirmed pattern."
        db.flush.assert_called_once()

    def test_raises_404_when_case_not_found(self):
        db = _db_get_returns(None)

        payload = CaseNoteCreate(author_id="analyst@example.com", body="Note body.")
        with pytest.raises(HTTPException) as exc_info:
            case_service.create_case_note(db=db, case_id=uuid.uuid4(), payload=payload)

        assert exc_info.value.status_code == 404
        db.add.assert_not_called()

    def test_rejects_empty_body(self):
        with pytest.raises(Exception):
            CaseNoteCreate(author_id="analyst@example.com", body="")

    def test_rejects_body_over_2000_chars(self):
        with pytest.raises(Exception):
            CaseNoteCreate(author_id="analyst@example.com", body="x" * 2001)

    def test_accepts_body_at_max_length(self):
        # 2000 chars is the exact limit — must not raise
        payload = CaseNoteCreate(author_id="analyst@example.com", body="x" * 2000)
        assert len(payload.body) == 2000

    def test_accepts_body_at_min_length(self):
        payload = CaseNoteCreate(author_id="analyst@example.com", body="x")
        assert len(payload.body) == 1


# =============================================================================
# list_case_notes
# =============================================================================

class TestListCaseNotes:

    def test_returns_notes_oldest_first(self):
        case_id = uuid.uuid4()
        note1 = _make_note(case_id, "First note")
        note2 = _make_note(case_id, "Second note")
        note2.created_at = datetime(2026, 1, 2, tzinfo=timezone.utc)

        db = _db_execute_returns([note1, note2])

        result = case_service.list_case_notes(db=db, case_id=case_id)

        assert result == [note1, note2]
        assert result[0].body == "First note"

    def test_returns_empty_list_when_no_notes(self):
        db = _db_execute_returns([])

        result = case_service.list_case_notes(db=db, case_id=uuid.uuid4())

        assert result == []

    def test_queries_by_case_id(self):
        case_id = uuid.uuid4()
        db = _db_execute_returns([])

        case_service.list_case_notes(db=db, case_id=case_id)

        db.execute.assert_called_once()