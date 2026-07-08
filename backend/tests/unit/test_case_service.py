#backend\tests\unit\test_case_service.py
"""
Unit tests for case_service.py — covers Case CRUD, CaseNote, and CaseEvent management.

Coverage:
    create_case()
        - persists case with correct defaults
        - auto-generates title from transaction_id
        - accepts explicit title and risk_level
        - writes an ALERT_ADDED event on creation

    list_cases()         - all / by status / by risk_level / by assigned_to
    get_case()           - found / 404
    update_case()        - status / risk_level / resolution_code / assigned_to
                         - ignores None fields
                         - 404 when not found
                         - writes STATUS_CHANGED event on status update
                         - writes ASSIGNMENT_CHANGED event on assignment

    create_case_note()
        - persists note linked to case
        - writes NOTE_ADDED event alongside note
        - 404 when case not found (no db.add called)
        - Pydantic rejects empty / oversized body

    list_case_notes()    - oldest-first / empty / queries by case_id

    list_case_events()   - newest-first / empty / queries by case_id
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from src.schemas.case_schemas import (
    CaseEventType,
    CaseNoteCreate,
    CaseResolutionCode,
    CaseRiskLevel,
    CaseStatus,
    CaseUpdate,
)
from src.services import case_service
from src.db.models.case_model import Case, CaseEvent, CaseNote


# =============================================================================
# Helpers
# =============================================================================

def _make_case(
    case_id: uuid.UUID | None = None,
    transaction_id: uuid.UUID | None = None,
    status: str = "OPEN",
    risk_level: str = "MEDIUM",
) -> Case:
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


def _make_event(
    case_id: uuid.UUID,
    event_type: str = "ALERT_ADDED",
    description: str = "Case opened automatically from fraud alert",
    actor: str = "system",
) -> CaseEvent:
    e = CaseEvent(case_id=case_id, event_type=event_type, description=description, actor=actor)
    e.id = uuid.uuid4()
    e.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return e


def _db_get_returns(obj):
    db = MagicMock()
    db.get.return_value = obj
    return db


def _db_execute_returns(rows: list):
    db = MagicMock()
    db.execute.return_value.scalars.return_value.all.return_value = rows
    return db


def _added_types(db) -> list[str]:
    """Return the class names of every object passed to db.add()."""
    return [type(c.args[0]).__name__ for c in db.add.call_args_list]


# =============================================================================
# create_case
# =============================================================================

class TestCreateCase:

    def test_persists_case_with_correct_defaults(self):
        db = MagicMock()
        txn_id = uuid.uuid4()

        case_service.create_case(db=db, transaction_id=txn_id)

        # First add is the Case, second is the ALERT_ADDED event
        assert _added_types(db)[0] == "Case"
        added: Case = db.add.call_args_list[0].args[0]
        assert added.transaction_id == txn_id
        assert added.status == CaseStatus.OPEN.value
        assert added.risk_level == CaseRiskLevel.MEDIUM.value
        db.flush.assert_called_once()

    def test_auto_generates_title_from_transaction_id(self):
        db = MagicMock()
        txn_id = uuid.UUID("abcd1234-0000-0000-0000-000000000000")

        case_service.create_case(db=db, transaction_id=txn_id)

        added: Case = db.add.call_args_list[0].args[0]
        assert "ABCD1234" in added.title

    def test_accepts_explicit_title(self):
        db = MagicMock()
        case_service.create_case(db=db, transaction_id=uuid.uuid4(), title="Custom Title")

        added: Case = db.add.call_args_list[0].args[0]
        assert added.title == "Custom Title"

    def test_accepts_explicit_risk_level(self):
        db = MagicMock()
        case_service.create_case(db=db, transaction_id=uuid.uuid4(), risk_level=CaseRiskLevel.HIGH)

        added: Case = db.add.call_args_list[0].args[0]
        assert added.risk_level == CaseRiskLevel.HIGH.value

    def test_writes_alert_added_event_on_creation(self):
        db = MagicMock()
        case_service.create_case(db=db, transaction_id=uuid.uuid4())

        types = _added_types(db)
        assert "CaseEvent" in types

        event: CaseEvent = next(c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], CaseEvent))
        assert event.event_type == CaseEventType.ALERT_ADDED.value
        assert event.actor == "system"


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
            db=db, case_id=case.id,
            payload=CaseUpdate(status=CaseStatus.INVESTIGATING),
        ))

        assert case.status == CaseStatus.INVESTIGATING.value

    def test_updates_risk_level(self):
        case = _make_case(risk_level="MEDIUM")
        db = _db_get_returns(case)

        asyncio.run(case_service.update_case(
            db=db, case_id=case.id,
            payload=CaseUpdate(risk_level=CaseRiskLevel.HIGH),
        ))

        assert case.risk_level == CaseRiskLevel.HIGH.value

    def test_updates_resolution_code(self):
        case = _make_case()
        db = _db_get_returns(case)

        asyncio.run(case_service.update_case(
            db=db, case_id=case.id,
            payload=CaseUpdate(resolution_code=CaseResolutionCode.CONFIRMED_FRAUD),
        ))

        assert case.resolution_code == CaseResolutionCode.CONFIRMED_FRAUD.value

    def test_updates_assigned_to(self):
        case = _make_case()
        analyst_id = uuid.uuid4()
        db = _db_get_returns(case)

        asyncio.run(case_service.update_case(
            db=db, case_id=case.id,
            payload=CaseUpdate(assigned_to=analyst_id),
        ))

        assert case.assigned_to == analyst_id

    def test_ignores_none_fields(self):
        case = _make_case(status="OPEN", risk_level="LOW")
        db = _db_get_returns(case)

        asyncio.run(case_service.update_case(
            db=db, case_id=case.id,
            payload=CaseUpdate(risk_level=CaseRiskLevel.HIGH),
        ))

        assert case.status == "OPEN"
        assert case.risk_level == CaseRiskLevel.HIGH.value

    def test_raises_404_when_case_not_found(self):
        db = _db_get_returns(None)

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(case_service.update_case(
                db=db, case_id=uuid.uuid4(),
                payload=CaseUpdate(status=CaseStatus.CLOSED),
            ))

        assert exc_info.value.status_code == 404

    def test_flushes_after_update(self):
        case = _make_case()
        db = _db_get_returns(case)

        asyncio.run(case_service.update_case(
            db=db, case_id=case.id,
            payload=CaseUpdate(status=CaseStatus.CLOSED),
        ))

        db.flush.assert_called_once()

    def test_writes_status_changed_event_on_status_update(self):
        case = _make_case(status="OPEN")
        db = _db_get_returns(case)

        asyncio.run(case_service.update_case(
            db=db, case_id=case.id,
            payload=CaseUpdate(status=CaseStatus.INVESTIGATING),
        ))

        types = _added_types(db)
        assert "CaseEvent" in types

        event: CaseEvent = next(c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], CaseEvent))
        assert event.event_type == CaseEventType.STATUS_CHANGED.value
        assert "OPEN" in event.description
        assert "INVESTIGATING" in event.description

    def test_writes_assignment_changed_event_on_assign(self):
        case = _make_case()
        analyst_id = uuid.uuid4()
        db = _db_get_returns(case)

        asyncio.run(case_service.update_case(
            db=db, case_id=case.id,
            payload=CaseUpdate(assigned_to=analyst_id),
        ))

        event: CaseEvent = next(c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], CaseEvent))
        assert event.event_type == CaseEventType.ASSIGNMENT_CHANGED.value

    def test_no_event_written_when_only_risk_level_updated(self):
        # risk_level change has no event — only status and assignment do
        case = _make_case()
        db = _db_get_returns(case)

        asyncio.run(case_service.update_case(
            db=db, case_id=case.id,
            payload=CaseUpdate(risk_level=CaseRiskLevel.HIGH),
        ))

        assert "CaseEvent" not in _added_types(db)


# =============================================================================
# create_case_note
# =============================================================================

class TestCreateCaseNote:

    def test_persists_note_linked_to_case(self):
        case = _make_case()
        db = _db_get_returns(case)

        payload = CaseNoteCreate(author_id="analyst@example.com", body="Confirmed pattern.")
        case_service.create_case_note(db=db, case_id=case.id, payload=payload)

        types = _added_types(db)
        assert "CaseNote" in types

        note: CaseNote = next(c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], CaseNote))
        assert note.case_id == case.id
        assert note.author_id == "analyst@example.com"
        assert note.body == "Confirmed pattern."
        db.flush.assert_called_once()

    def test_writes_note_added_event_alongside_note(self):
        case = _make_case()
        db = _db_get_returns(case)

        payload = CaseNoteCreate(author_id="analyst@example.com", body="Review complete.")
        case_service.create_case_note(db=db, case_id=case.id, payload=payload)

        types = _added_types(db)
        assert types.count("CaseNote") == 1
        assert types.count("CaseEvent") == 1

        event: CaseEvent = next(c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], CaseEvent))
        assert event.event_type == CaseEventType.NOTE_ADDED.value
        assert event.actor == "analyst@example.com"

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
        db = _db_execute_returns([])

        case_service.list_case_notes(db=db, case_id=uuid.uuid4())

        db.execute.assert_called_once()


# =============================================================================
# list_case_events
# =============================================================================

class TestListCaseEvents:

    def test_returns_events_newest_first(self):
        case_id = uuid.uuid4()
        event1 = _make_event(case_id, "ALERT_ADDED")
        event2 = _make_event(case_id, "STATUS_CHANGED")
        event2.created_at = datetime(2026, 1, 2, tzinfo=timezone.utc)
        # Service orders desc so newest (event2) comes first
        db = _db_execute_returns([event2, event1])

        result = case_service.list_case_events(db=db, case_id=case_id)

        assert result[0].event_type == "STATUS_CHANGED"
        assert result[1].event_type == "ALERT_ADDED"

    def test_returns_empty_list_when_no_events(self):
        db = _db_execute_returns([])

        result = case_service.list_case_events(db=db, case_id=uuid.uuid4())

        assert result == []

    def test_queries_by_case_id(self):
        db = _db_execute_returns([])

        case_service.list_case_events(db=db, case_id=uuid.uuid4())

        db.execute.assert_called_once()

    def test_event_fields_are_correct(self):
        case_id = uuid.uuid4()
        event = _make_event(case_id, "NOTE_ADDED", "Note added", "analyst@example.com")
        db = _db_execute_returns([event])

        result = case_service.list_case_events(db=db, case_id=case_id)

        assert result[0].event_type == "NOTE_ADDED"
        assert result[0].description == "Note added"
        assert result[0].actor == "analyst@example.com"
        assert result[0].case_id == case_id