"""Unit tests for the /transactions ingest pipeline."""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.schemas.decision_schemas import Decision
from src.schemas.scoring_schemas import (
    AuthenticationMethod,
    AvsResult,
    CardType,
    Channel,
    CvvResult,
    PanEntryMode,
    TransactionType,
)
from src.schemas.transaction_ingest import TransactionIngestRequest
from src.services import decision_service
from src.services.decision_service import (
    _build_card_history,
    _build_transaction,
    _map_decision,
    _serialize_detail,
    _serialize_list_item,
    get_transaction,
)

# Convenience aliases matching the Decision enum values
APPROVE            = Decision.APPROVE.value
APPROVE_WITH_REVIEW = Decision.APPROVE_WITH_REVIEW.value
DECLINE            = Decision.DECLINE.value

# =============================================================================
# Helpers
# =============================================================================

THRESHOLDS = {"approve_below": 0.10, "decline_from": 0.80}


def _payload(**overrides) -> TransactionIngestRequest:
    base = dict(
        card_id="CARD-1",
        merchant_id="MRCH-1",
        timestamp=datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc),
        enriched_amount_usd=42.5,
        issuing_bank_country="KE",
        transaction_country="KE",
        cvv2_result=CvvResult.MATCH,
        avs_result=AvsResult.FULL_MATCH,
        pan_entry_mode=PanEntryMode.CHIP,
        authentication=AuthenticationMethod.PIN if hasattr(AuthenticationMethod, "PIN") else list(AuthenticationMethod)[0],
        card_type=CardType.DEBIT,
        channel=Channel.POS,
        transaction_type=TransactionType.PURCHASE,
        merchant_category_code="5411",
    )
    base.update(overrides)
    return TransactionIngestRequest(**base)


def _txn_row(**overrides):
    base = dict(
        id=uuid.uuid4(),
        transaction_amount=Decimal("1500.00"),
        transaction_currency="KES",
        merchant_id="MRCH-1001",
        ts=datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc),
        lifecycle_status="AUTHORIZED",
        is_simulated=False,
        is_manually_created=False,
        created_at=datetime(2026, 5, 31, 12, 0, 1, tzinfo=timezone.utc),
        decision=APPROVE,
        card_id="CARD-42",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


# =============================================================================
# _map_decision
# =============================================================================

class TestMapDecision:
    def test_below_approve_threshold(self):
        assert _map_decision(0.05, THRESHOLDS) == Decision.APPROVE

    def test_exactly_at_approve_below_is_review(self):
        assert _map_decision(0.10, THRESHOLDS) == Decision.APPROVE_WITH_REVIEW

    def test_middle_zone_is_review(self):
        assert _map_decision(0.50, THRESHOLDS) == Decision.APPROVE_WITH_REVIEW

    def test_exactly_at_decline_from_is_decline(self):
        assert _map_decision(0.80, THRESHOLDS) == Decision.DECLINE

    def test_above_decline_threshold(self):
        assert _map_decision(0.95, THRESHOLDS) == Decision.DECLINE


# =============================================================================
# _build_card_history
# =============================================================================

class TestBuildCardHistory:
    def _db_with_rows(self, rows):
        db = MagicMock()
        db.execute.return_value.all.return_value = rows
        return db

    def test_cold_start_no_prior_rows(self):
        db = self._db_with_rows([])
        payload = _payload(enriched_amount_usd=123.0)

        history = _build_card_history(db, payload)

        assert history["txn_count"] == 0
        assert history["mean_amt"] == 123.0
        assert history["std_amt"] == 1.0
        assert history["last_ts"] is None
        assert history["recent_timestamps"] == []
        assert history["current_ts"] == payload.timestamp.timestamp()

    def test_with_history_computes_mean_and_std(self):
        ts1 = datetime(2026, 5, 30, 10, 0, tzinfo=timezone.utc)
        ts2 = datetime(2026, 5, 30, 11, 0, tzinfo=timezone.utc)
        rows = [
            SimpleNamespace(enriched_amount_usd=Decimal("10"), ts=ts1),
            SimpleNamespace(enriched_amount_usd=Decimal("20"), ts=ts2),
        ]
        db = self._db_with_rows(rows)
        payload = _payload()

        history = _build_card_history(db, payload)

        assert history["txn_count"] == 2
        assert history["mean_amt"] == 15.0
        assert history["std_amt"] > 0
        assert history["last_ts"] == ts2.timestamp()
        assert len(history["recent_timestamps"]) == 2

    def test_single_prior_row_uses_std_fallback(self):
        ts1 = datetime(2026, 5, 30, 10, 0, tzinfo=timezone.utc)
        rows = [SimpleNamespace(enriched_amount_usd=Decimal("50"), ts=ts1)]
        db = self._db_with_rows(rows)

        history = _build_card_history(db, _payload())

        assert history["txn_count"] == 1
        assert history["mean_amt"] == 50.0
        assert history["std_amt"] == 1.0


# =============================================================================
# _build_transaction
# =============================================================================

class TestBuildTransaction:
    def test_amount_fallback_to_enriched_usd(self):
        payload = _payload(transaction_amount=None, transaction_currency=None)

        txn = _build_transaction(payload, decision=Decision.APPROVE, reason_code=None)

        assert txn.transaction_amount == Decimal(str(payload.enriched_amount_usd))
        assert txn.transaction_currency == "USD"
        assert txn.decision == Decision.APPROVE.value
        assert txn.reason_code is None
        assert txn.is_fraud is None

    def test_explicit_amount_and_currency_kept(self):
        payload = _payload(transaction_amount=Decimal("999.00"), transaction_currency="KES")

        txn = _build_transaction(payload, decision=Decision.DECLINE, reason_code="MERCHANT_BLACKLISTED")

        assert txn.transaction_amount == Decimal("999.00")
        assert txn.transaction_currency == "KES"
        assert txn.decision == Decision.DECLINE.value
        assert txn.reason_code == "MERCHANT_BLACKLISTED"

    def test_aligned_columns_persisted(self):
        payload = _payload(transaction_type=TransactionType.WITHDRAWAL, transaction_country="UG")

        txn = _build_transaction(payload, decision=Decision.APPROVE, reason_code=None)

        assert txn.transaction_type == "withdrawal"
        assert txn.transaction_country == "UG"


# =============================================================================
# TransactionIngestRequest.scoring_transaction
# =============================================================================

def test_scoring_transaction_converts_enums_to_strings():
    payload = _payload()
    scorer_dict = payload.scoring_transaction()

    assert isinstance(scorer_dict["card_type"], str)
    assert isinstance(scorer_dict["channel"], str)
    assert isinstance(scorer_dict["transaction_type"], str)
    assert scorer_dict["transaction_type"] == "purchase"
    assert "merchant_id" not in scorer_dict
    assert "transaction_amount" not in scorer_dict
    assert "user_ip" not in scorer_dict


# =============================================================================
# ingest() — blacklist short-circuit
# =============================================================================

def test_ingest_blacklist_short_circuits_without_scoring():
    db = MagicMock()
    fake_id = uuid.uuid4()

    def _flush_assigns_id():
        for call in db.add.call_args_list:
            call.args[0].id = fake_id

    db.flush.side_effect = _flush_assigns_id

    with patch.object(decision_service, "is_merchant_blacklisted", return_value=True), \
         patch.object(decision_service, "score_transaction", new=AsyncMock()) as mock_score:
        resp = asyncio.run(decision_service.ingest(db, _payload(), explain=False))

    mock_score.assert_not_called()
    assert resp.decision == Decision.DECLINE.value
    assert resp.score is None
    assert resp.reason == "merchant_blacklisted"
    db.commit.assert_called_once()


def test_ingest_blacklist_short_circuits_without_scoring_and_no_alert():
    db = MagicMock()
    fake_id = uuid.uuid4()

    def _flush_assigns_id():
        for call in db.add.call_args_list:
            call.args[0].id = fake_id

    db.flush.side_effect = _flush_assigns_id

    with patch.object(decision_service, "is_merchant_blacklisted", return_value=True), \
         patch.object(decision_service, "score_transaction", new=AsyncMock()) as mock_score:
        resp = asyncio.run(decision_service.ingest(db, _payload(), explain=False))

    mock_score.assert_not_called()
    assert resp.decision == Decision.DECLINE.value
    assert resp.score is None
    db.commit.assert_called_once()


# =============================================================================
# ingest() — clean scoring path
# =============================================================================

def test_ingest_clean_path_scores_and_persists():
    db = MagicMock()
    db.execute.return_value.all.return_value = []

    fake_id = uuid.uuid4()
    db.flush.side_effect = lambda: [
        setattr(c.args[0], "id", fake_id) for c in db.add.call_args_list
        if not getattr(c.args[0], "id", None)
    ]

    score_result = {
        "score": 0.05,
        "model_name": "calibrated_lightgbm_version2",
        "contributions": None,
    }

    with patch.object(decision_service, "is_merchant_blacklisted", return_value=False), \
         patch.object(decision_service, "score_transaction", new=AsyncMock(return_value=score_result)), \
         patch.object(decision_service, "get_feature_schema", new=AsyncMock(return_value={"thresholds": THRESHOLDS})), \
         patch.object(decision_service.event_emitter, "emit"):
        resp = asyncio.run(decision_service.ingest(db, _payload(), explain=False))

    assert resp.decision == Decision.APPROVE.value
    assert resp.score == 0.05
    assert resp.model_name == "calibrated_lightgbm_version2"
    assert db.add.call_count == 2   # Transaction + FraudScore
    db.commit.assert_called_once()


def test_ingest_explain_persists_score_reasons():
    db = MagicMock()
    db.execute.return_value.all.return_value = []

    fake_id = uuid.uuid4()
    db.flush.side_effect = lambda: [
        setattr(c.args[0], "id", fake_id) for c in db.add.call_args_list
        if not getattr(c.args[0], "id", None)
    ]

    score_result = {
        "score": 0.92,
        "model_name": "calibrated_lightgbm_version2",
        "contributions": [
            {"feature": "amount_zscore", "value": 2.5, "shap_value": 0.4},
            {"feature": "cross_border",  "value": 1.0, "shap_value": -0.1},
        ],
    }

    with patch.object(decision_service, "is_merchant_blacklisted", return_value=False), \
         patch.object(decision_service, "score_transaction", new=AsyncMock(return_value=score_result)), \
         patch.object(decision_service, "get_feature_schema", new=AsyncMock(return_value={"thresholds": THRESHOLDS})), \
         patch.object(decision_service.event_emitter, "emit"):   # mock emitter — no alert db.add
        resp = asyncio.run(decision_service.ingest(db, _payload(), explain=True))

    assert resp.decision == Decision.DECLINE.value
    # Transaction + FraudScore + 2 ScoreReasons = 4
    assert db.add.call_count == 4
    added_types = [type(c.args[0]).__name__ for c in db.add.call_args_list]
    assert added_types.count("Transaction") == 1
    assert added_types.count("FraudScore") == 1
    assert added_types.count("ScoreReason") == 2

    reasons = [c.args[0] for c in db.add.call_args_list if type(c.args[0]).__name__ == "ScoreReason"]
    directions = {r.feature: r.direction for r in reasons}
    assert directions["amount_zscore"] == "HIGH"
    assert directions["cross_border"] == "LOW"


# =============================================================================
# ingest() — scorer failure persists nothing
# =============================================================================

def test_ingest_scorer_failure_writes_nothing():
    from fastapi import HTTPException

    db = MagicMock()
    db.execute.return_value.all.return_value = []

    with patch.object(decision_service, "is_merchant_blacklisted", return_value=False), \
         patch.object(decision_service, "score_transaction", new=AsyncMock(side_effect=HTTPException(503, "model down"))):
        with pytest.raises(HTTPException):
            asyncio.run(decision_service.ingest(db, _payload(), explain=False))

    db.add.assert_not_called()
    db.commit.assert_not_called()


# =============================================================================
# READ — serialization helpers
# =============================================================================

class TestSerializeListItem:
    def test_without_score(self):
        data = _serialize_list_item(_txn_row(), None)
        assert data["merchant_id"] == "MRCH-1001"
        assert data["score"] is None
        assert data["model_version"] is None

    def test_with_score(self):
        score = SimpleNamespace(score=Decimal("0.42"), model_version="version2")
        data = _serialize_list_item(_txn_row(), score)
        assert data["score"] == 0.42
        assert data["model_version"] == "version2"


class TestSerializeDetail:
    def test_includes_reasons_and_features(self):
        txn = _txn_row()
        score = SimpleNamespace(
            score=Decimal("0.82"),
            model_version="version2",
            features_snapshot={"amount_zscore": 2.1, "cross_border": True},
        )
        reasons = [
            SimpleNamespace(
                id=uuid.uuid4(),
                score_id=uuid.uuid4(),
                feature="amount_zscore",
                direction="HIGH",
                contribution=Decimal("0.31"),
            )
        ]
        data = _serialize_detail(txn, score, reasons)
        assert data["score"] == 0.82
        assert len(data["reasons"]) == 1
        assert data["reasons"][0]["feature"] == "amount_zscore"
        assert data["features"]["cross_border"] is True


class TestGetTransaction:
    def test_not_found_raises_404(self):
        from fastapi import HTTPException

        db = MagicMock()
        db.get.return_value = None

        with pytest.raises(HTTPException) as exc:
            asyncio.run(get_transaction(db, uuid.uuid4()))

        assert exc.value.status_code == 404

    def test_returns_detail_payload(self):
        txn_id = uuid.uuid4()
        txn = _txn_row(id=txn_id)
        score = SimpleNamespace(
            id=uuid.uuid4(),
            score=Decimal("0.55"),
            model_version="version2",
            features_snapshot={"is_night": False},
            scored_at=datetime(2026, 5, 31, 12, 1, tzinfo=timezone.utc),
            is_rescore=False,
            transaction_id=txn_id,
        )
        reason = SimpleNamespace(
            id=uuid.uuid4(),
            score_id=score.id,
            feature="velocity_spike_1h",
            direction="HIGH",
            contribution=Decimal("0.18"),
        )

        db = MagicMock()
        db.get.return_value = txn
        score_result = MagicMock()
        score_result.scalar_one_or_none.return_value = score
        reasons_result = MagicMock()
        reasons_result.scalars.return_value.all.return_value = [reason]
        db.execute.side_effect = [score_result, reasons_result]

        data = asyncio.run(get_transaction(db, txn_id))

        assert data["id"] == str(txn_id)
        assert data["score"] == 0.55
        assert data["reasons"][0]["feature"] == "velocity_spike_1h"
        assert data["features"]["is_night"] is False