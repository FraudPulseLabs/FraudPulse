#backend\tests\unit\test_alert_service.py
"""
Unit tests for alert event generation.

Verifies that transaction decisioning emits the correct domain events:
    * DECLINE -> fraud_decline
    * APPROVE_WITH_REVIEW -> fraud_review_required
    * APPROVE -> no event
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

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


def _payload(**overrides: Any) -> TransactionIngestRequest:
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
        authentication=(
            AuthenticationMethod.PIN
            if hasattr(AuthenticationMethod, "PIN")
            else list(AuthenticationMethod)[0]
        ),
        card_type=CardType.DEBIT,
        channel=Channel.POS,
        transaction_type=TransactionType.PURCHASE,
        merchant_category_code="5411",
    )

    base.update(overrides)
    return TransactionIngestRequest(**base)


# =============================================================================
# Alert event generation
# =============================================================================


# DECLINE emits fraud_decline event.
def test_ingest_decline_emits_alert_event():
    db = MagicMock()
    db.execute.return_value.all.return_value = []

    fake_id = uuid.uuid4()

    db.flush.side_effect = lambda: [
        setattr(c.args[0], "id", fake_id)
        for c in db.add.call_args_list
        if not getattr(c.args[0], "id", None)
    ]

    score_result = {
        "score": 0.95,
        "model_name": "calibrated_lightgbm_version2",
        "contributions": None,
    }

    with (
        patch.object(
            decision_service,
            "is_merchant_blacklisted",
            return_value=False,
        ),
        patch.object(
            decision_service,
            "score_transaction",
            new=AsyncMock(return_value=score_result),
        ),
        patch.object(
            decision_service,
            "get_feature_schema",
            new=AsyncMock(
                return_value={
                    "thresholds": {
                        "approve_below": 0.1,
                        "decline_from": 0.8,
                    }
                }
            ),
        ),
        patch.object(
            decision_service.event_emitter,
            "emit",
        ) as mock_emit,
    ):
        resp = asyncio.run(
            decision_service.ingest(
                db,
                _payload(),
                explain=False,
            )
        )

    assert resp.decision == Decision.DECLINE

    mock_emit.assert_called_once_with(
        "fraud_decline",
        db=db,
        transaction_id=fake_id,
    )


# APPROVE_WITH_REVIEW emits fraud_review_required event.
def test_ingest_review_emits_alert_event():
    db = MagicMock()
    db.execute.return_value.all.return_value = []

    fake_id = uuid.uuid4()

    db.flush.side_effect = lambda: [
        setattr(c.args[0], "id", fake_id)
        for c in db.add.call_args_list
        if not getattr(c.args[0], "id", None)
    ]

    score_result = {
        "score": 0.50,
        "model_name": "calibrated_lightgbm_version2",
        "contributions": None,
    }

    with (
        patch.object(
            decision_service,
            "is_merchant_blacklisted",
            return_value=False,
        ),
        patch.object(
            decision_service,
            "score_transaction",
            new=AsyncMock(return_value=score_result),
        ),
        patch.object(
            decision_service,
            "get_feature_schema",
            new=AsyncMock(
                return_value={
                    "thresholds": {
                        "approve_below": 0.1,
                        "decline_from": 0.8,
                    }
                }
            ),
        ),
        patch.object(
            decision_service.event_emitter,
            "emit",
        ) as mock_emit,
    ):
        resp = asyncio.run(
            decision_service.ingest(
                db,
                _payload(),
                explain=False,
            )
        )

    assert resp.decision == Decision.APPROVE_WITH_REVIEW

    mock_emit.assert_called_once_with(
        "fraud_review_required",
        db=db,
        transaction_id=fake_id,
    )


# APPROVE emits no alert event.
def test_ingest_approve_emits_no_alert_event():
    db = MagicMock()
    db.execute.return_value.all.return_value = []

    fake_id = uuid.uuid4()

    db.flush.side_effect = lambda: [
        setattr(c.args[0], "id", fake_id)
        for c in db.add.call_args_list
        if not getattr(c.args[0], "id", None)
    ]

    score_result = {
        "score": 0.05,
        "model_name": "calibrated_lightgbm_version2",
        "contributions": None,
    }

    with (
        patch.object(
            decision_service,
            "is_merchant_blacklisted",
            return_value=False,
        ),
        patch.object(
            decision_service,
            "score_transaction",
            new=AsyncMock(return_value=score_result),
        ),
        patch.object(
            decision_service,
            "get_feature_schema",
            new=AsyncMock(
                return_value={
                    "thresholds": {
                        "approve_below": 0.1,
                        "decline_from": 0.8,
                    }
                }
            ),
        ),
        patch.object(
            decision_service.event_emitter,
            "emit",
        ) as mock_emit,
    ):
        resp = asyncio.run(
            decision_service.ingest(
                db,
                _payload(),
                explain=False,
            )
        )

    assert resp.decision == Decision.APPROVE
    mock_emit.assert_not_called()