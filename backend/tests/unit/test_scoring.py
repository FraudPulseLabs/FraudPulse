"""
tests/unit/test_scoring.py
============================
pytest suite for scoring_service.py and scoring_routes.py.

Run from the backend/ directory:
    pytest tests/unit/test_scoring.py -v

The real model artefact and RealtimeFeatureBuilder are mocked throughout so
these tests remain fast and artefact-free in CI.

Coverage:
    score_transaction()
        - happy path (explain=False / explain=True)
        - RuntimeError → 503
        - unexpected Exception → 500
        - contributions sorted by abs(shap_value) descending
        - contributions=None when explain=False
        - card_id present / absent in log context

    _to_dataframe()
        - shape and column names

    _extract_lgbm_booster()
        - happy path (CalibratedClassifierCV-like structure)
        - graceful fallback when attribute missing

    _compute_contributions()
        - returns [] when booster is None
        - returns [] when booster.predict raises
        - correct length, field names, sorting
        - bias column dropped (last column of pred_contrib)

    get_feature_schema()
        - delegates to builder._schema

    POST /score route
        - 200 with valid payload
        - 200 with explain=True
        - 422 on invalid payload (pydantic validation)
        - explain query param forwarded to service

    GET /schema route
        - 200, returns schema dict
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# We import from the source tree.  Adjust sys.path if your project layout
# differs from the one described in the module docstrings.
# ---------------------------------------------------------------------------
from src.services.scoring_service import (
    _compute_contributions,
    _extract_lgbm_booster,
    _to_dataframe,
    get_feature_schema,
    score_transaction,
)
from src.api.v1.scoring_routes import router


# =============================================================================
# SHARED FIXTURES
# =============================================================================

FEATURE_ORDER = ["f1", "f2", "f3"]
N_FEATURES    = len(FEATURE_ORDER)


@pytest.fixture
def feature_order() -> list[str]:
    return list(FEATURE_ORDER)


@pytest.fixture
def sample_vector() -> np.ndarray:
    return np.array([[0.1, 0.5, 0.9]], dtype=np.float32)


@pytest.fixture
def sample_features() -> dict:
    return {"f1": 0.1, "f2": 0.5, "f3": 0.9}


@pytest.fixture
def mock_builder(feature_order, sample_features, sample_vector):
    builder = MagicMock()
    builder.feature_order = feature_order
    builder.feature_count = len(feature_order)
    builder._schema       = {"model_name": "lgbm_v2", "features": feature_order}
    builder.build.return_value = (sample_features, sample_vector)
    return builder


@pytest.fixture
def mock_model():
    model = MagicMock()
    model.predict_proba.return_value = np.array([[0.85, 0.15]])
    return model


# --- Transaction / history dicts used across tests -------------------------

@pytest.fixture
def txn_dict() -> dict:
    return {
        "card_id":                "card-abc",
        "timestamp":              datetime(2024, 6, 15, 14, 30, tzinfo=timezone.utc),
        "enriched_amount_usd":    85.00,
        "issuing_bank_country":   "US",
        "transaction_country":    "US",
        "cvv2_result":            "MATCH",
        "avs_result":             "FULL_MATCH",
        "pan_entry_mode":         "CHIP",
        "authentication":         "PIN",
        "card_type":              "Debit",
        "channel":                "POS",
        "transaction_type":       "purchase",
        "merchant_category_code": "5411",
    }


@pytest.fixture
def history_dict() -> dict:
    return {
        "txn_count":         42,
        "mean_amt":          78.50,
        "std_amt":           22.10,
        "last_ts":           1718450000.0,
        "current_ts":        1718453600.0,
        "recent_timestamps": [1718450000.0, 1718449000.0],
    }


# --- FastAPI test client ---------------------------------------------------

@pytest.fixture(scope="module")
def api_client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


# --- Full API payload -------------------------------------------------------

@pytest.fixture
def valid_api_payload() -> dict:
    return {
        "transaction": {
            "card_id":                "card-xyz",
            "timestamp":              "2024-06-15T14:30:00Z",
            "enriched_amount_usd":    120.00,
            "issuing_bank_country":   "US",
            "transaction_country":    "US",
            "cvv2_result":            "MATCH",
            "avs_result":             "FULL_MATCH",
            "pan_entry_mode":         "CHIP",
            "authentication":         "PIN",
            "card_type":              "Debit",
            "channel":                "POS",
            "transaction_type":       "purchase",
            "merchant_category_code": "5411",
        },
        "card_history": {
            "txn_count":         10,
            "mean_amt":          80.0,
            "std_amt":           20.0,
            "last_ts":           1718450000.0,
            "current_ts":        1718453600.0,
            "recent_timestamps": [],
        },
    }


# =============================================================================
# _to_dataframe
# =============================================================================

class TestToDataframe:

    def test_returns_dataframe(self, sample_vector, feature_order):
        df = _to_dataframe(sample_vector, feature_order)
        assert isinstance(df, pd.DataFrame)

    def test_column_names_match_feature_order(self, sample_vector, feature_order):
        df = _to_dataframe(sample_vector, feature_order)
        assert list(df.columns) == feature_order

    def test_values_preserved(self, sample_vector, feature_order):
        df = _to_dataframe(sample_vector, feature_order)
        np.testing.assert_array_almost_equal(df.values, sample_vector)

    def test_shape_matches_vector(self, sample_vector, feature_order):
        df = _to_dataframe(sample_vector, feature_order)
        assert df.shape == sample_vector.shape


# =============================================================================
# _extract_lgbm_booster
# =============================================================================

class TestExtractLgbmBooster:

    def test_returns_booster_from_calibrated_wrapper(self):
        booster  = MagicMock(name="booster")
        estimator = MagicMock()
        estimator.booster_ = booster
        calibrated = MagicMock()
        calibrated.estimator = estimator
        model = MagicMock()
        model.calibrated_classifiers_ = [calibrated]

        result = _extract_lgbm_booster(model)
        assert result is booster

    def test_returns_none_when_attribute_missing(self):
        model = MagicMock(spec=[])   # no calibrated_classifiers_
        result = _extract_lgbm_booster(model)
        assert result is None

    def test_returns_none_when_list_is_empty(self):
        model = MagicMock()
        model.calibrated_classifiers_ = []
        result = _extract_lgbm_booster(model)
        assert result is None

    def test_returns_none_when_estimator_lacks_booster(self):
        calibrated = MagicMock(spec=["estimator"])
        calibrated.estimator = MagicMock(spec=[])  # no .booster_
        model = MagicMock()
        model.calibrated_classifiers_ = [calibrated]
        result = _extract_lgbm_booster(model)
        assert result is None


# =============================================================================
# _compute_contributions
# =============================================================================

class TestComputeContributions:

    @pytest.fixture
    def booster_model(self, feature_order):
        """A model whose booster returns n_features + 1 pred_contrib columns."""
        n = len(feature_order)
        shap_raw     = np.array([[0.3, -0.1, 0.5, 0.0]])  # last col = bias
        booster      = MagicMock()
        booster.predict.return_value = shap_raw

        estimator = MagicMock()
        estimator.booster_ = booster
        calibrated = MagicMock()
        calibrated.estimator = estimator
        model = MagicMock()
        model.calibrated_classifiers_ = [calibrated]
        return model

    def test_returns_empty_list_when_booster_is_none(
        self, feature_order, sample_features
    ):
        model = MagicMock(spec=[])
        df = pd.DataFrame([[0.1, 0.5, 0.9]], columns=feature_order)
        result = _compute_contributions(model, df, sample_features, feature_order)
        assert result == []

    def test_returns_empty_list_when_predict_raises(
        self, feature_order, sample_features
    ):
        booster = MagicMock()
        booster.predict.side_effect = RuntimeError("boom")
        estimator = MagicMock()
        estimator.booster_ = booster
        calibrated = MagicMock()
        calibrated.estimator = estimator
        model = MagicMock()
        model.calibrated_classifiers_ = [calibrated]

        df = pd.DataFrame([[0.1, 0.5, 0.9]], columns=feature_order)
        result = _compute_contributions(model, df, sample_features, feature_order)
        assert result == []

    def test_correct_length(self, booster_model, feature_order, sample_features):
        df = pd.DataFrame([[0.1, 0.5, 0.9]], columns=feature_order)
        result = _compute_contributions(booster_model, df, sample_features, feature_order)
        assert len(result) == len(feature_order)

    def test_bias_column_dropped(self, booster_model, feature_order, sample_features):
        """Result must have exactly n_features entries — not n_features + 1."""
        df = pd.DataFrame([[0.1, 0.5, 0.9]], columns=feature_order)
        result = _compute_contributions(booster_model, df, sample_features, feature_order)
        assert len(result) == len(feature_order)

    def test_sorted_by_abs_shap_descending(self, booster_model, feature_order, sample_features):
        """
        booster returns [0.3, -0.1, 0.5] (bias dropped).
        abs values: f3=0.5, f1=0.3, f2=0.1 → f3 first.
        """
        df = pd.DataFrame([[0.1, 0.5, 0.9]], columns=feature_order)
        result = _compute_contributions(booster_model, df, sample_features, feature_order)
        abs_values = [abs(r["shap_value"]) for r in result]
        assert abs_values == sorted(abs_values, reverse=True)

    def test_contribution_dict_has_required_keys(self, booster_model, feature_order, sample_features):
        df = pd.DataFrame([[0.1, 0.5, 0.9]], columns=feature_order)
        result = _compute_contributions(booster_model, df, sample_features, feature_order)
        for entry in result:
            assert set(entry.keys()) == {"feature", "value", "shap_value"}

    def test_feature_value_comes_from_features_dict(
        self, booster_model, feature_order, sample_features
    ):
        df = pd.DataFrame([[0.1, 0.5, 0.9]], columns=feature_order)
        result = _compute_contributions(booster_model, df, sample_features, feature_order)
        result_by_name = {r["feature"]: r for r in result}
        for name, expected_val in sample_features.items():
            assert result_by_name[name]["value"] == pytest.approx(expected_val)

    def test_booster_receives_numpy_array_not_dataframe(
        self, booster_model, feature_order, sample_features
    ):
        """booster_.predict() must receive .values (ndarray), not a DataFrame."""
        df = pd.DataFrame([[0.1, 0.5, 0.9]], columns=feature_order)
        _compute_contributions(booster_model, df, sample_features, feature_order)
        call_args = booster_model.calibrated_classifiers_[0].estimator.booster_.predict.call_args
        first_arg = call_args[0][0]
        assert isinstance(first_arg, np.ndarray)


# =============================================================================
# score_transaction
# =============================================================================

class TestScoreTransaction:

    @pytest.fixture(autouse=True)
    def patch_singletons(self, mock_model, mock_builder):
        """Replace the lru_cache singletons with mocks for every test."""
        with (
            patch("src.services.scoring_service._get_model", return_value=mock_model),
            patch("src.services.scoring_service._get_builder", return_value=mock_builder),
        ):
            yield

    # --- Happy path --------------------------------------------------------

    def test_returns_score_in_range(self, txn_dict, history_dict, mock_model):
        mock_model.predict_proba.return_value = np.array([[0.92, 0.08]])
        result = asyncio.run(
            score_transaction(txn_dict, history_dict)
        )
        assert 0.0 <= result["score"] <= 1.0

    def test_score_matches_model_output(self, txn_dict, history_dict, mock_model):
        mock_model.predict_proba.return_value = np.array([[0.72, 0.28]])
        result = asyncio.run(
            score_transaction(txn_dict, history_dict)
        )
        assert result["score"] == pytest.approx(0.28)

    def test_model_name_in_response(self, txn_dict, history_dict):
        result = asyncio.run(
            score_transaction(txn_dict, history_dict)
        )
        assert result["model_name"] == "lgbm_v2"

    def test_contributions_none_when_explain_false(self, txn_dict, history_dict):
        result = asyncio.run(
            score_transaction(txn_dict, history_dict, explain=False)
        )
        assert result["contributions"] is None

    def test_contributions_present_when_explain_true(self, txn_dict, history_dict, mock_model):
        shap_raw = np.array([[0.1, 0.2, 0.05, 0.0]])
        booster  = MagicMock()
        booster.predict.return_value = shap_raw
        estimator = MagicMock()
        estimator.booster_ = booster
        calibrated = MagicMock()
        calibrated.estimator = estimator
        mock_model.calibrated_classifiers_ = [calibrated]

        result = asyncio.run(
            score_transaction(txn_dict, history_dict, explain=True)
        )
        assert result["contributions"] is not None
        assert isinstance(result["contributions"], list)
        assert len(result["contributions"]) == len(FEATURE_ORDER)

    def test_contributions_sorted_descending_by_abs_shap(
        self, txn_dict, history_dict, mock_model
    ):
        shap_raw = np.array([[0.05, 0.5, 0.1, 0.0]])
        booster  = MagicMock()
        booster.predict.return_value = shap_raw
        estimator = MagicMock()
        estimator.booster_ = booster
        calibrated = MagicMock()
        calibrated.estimator = estimator
        mock_model.calibrated_classifiers_ = [calibrated]

        result = asyncio.run(
            score_transaction(txn_dict, history_dict, explain=True)
        )
        abs_vals = [abs(c["shap_value"]) for c in result["contributions"]]
        assert abs_vals == sorted(abs_vals, reverse=True)

    def test_response_keys(self, txn_dict, history_dict):
        result = asyncio.run(
            score_transaction(txn_dict, history_dict)
        )
        assert set(result.keys()) == {"score", "model_name", "contributions"}

    # --- Error paths -------------------------------------------------------

    def test_runtime_error_raises_503(self, txn_dict, history_dict):
        from fastapi import HTTPException
        with patch(
            "src.services.scoring_service._get_model",
            side_effect=RuntimeError("Model artefact not found"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(
                    score_transaction(txn_dict, history_dict)
                )
            assert exc_info.value.status_code == 503

    def test_unexpected_exception_raises_500(self, txn_dict, history_dict, mock_builder):
        mock_builder.build.side_effect = ValueError("unexpected")
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(
                score_transaction(txn_dict, history_dict)
            )
        assert exc_info.value.status_code == 500

    def test_500_detail_message(self, txn_dict, history_dict, mock_builder):
        mock_builder.build.side_effect = ValueError("unexpected")
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(
                score_transaction(txn_dict, history_dict)
            )
        assert "fraud scoring failed" in exc_info.value.detail.lower()

    def test_missing_card_id_still_scores(self, history_dict, mock_model):
        """card_id is absent from internal dicts; service must not crash."""
        txn_without_id = {
            "timestamp":              datetime(2024, 6, 15, 14, 30, tzinfo=timezone.utc),
            "enriched_amount_usd":    85.00,
            "issuing_bank_country":   "US",
            "transaction_country":    "US",
            "cvv2_result":            "MATCH",
            "avs_result":             "FULL_MATCH",
            "pan_entry_mode":         "CHIP",
            "authentication":         "PIN",
            "card_type":              "Debit",
            "channel":                "POS",
            "transaction_type":       "purchase",
            "merchant_category_code": "5411",
        }
        mock_model.predict_proba.return_value = np.array([[0.8, 0.2]])
        result = asyncio.run(
            score_transaction(txn_without_id, history_dict)
        )
        assert "score" in result


# =============================================================================
# get_feature_schema
# =============================================================================

class TestGetFeatureSchema:

    def test_returns_schema_dict(self, mock_builder):
        with patch("src.services.scoring_service._get_builder", return_value=mock_builder):
            result = asyncio.run(get_feature_schema())
        assert result == mock_builder._schema

    def test_schema_contains_model_name(self, mock_builder):
        with patch("src.services.scoring_service._get_builder", return_value=mock_builder):
            result = asyncio.run(get_feature_schema())
        assert "model_name" in result

    def test_schema_contains_features(self, mock_builder):
        with patch("src.services.scoring_service._get_builder", return_value=mock_builder):
            result = asyncio.run(get_feature_schema())
        assert "features" in result
        assert isinstance(result["features"], list)


# =============================================================================
# POST /score route
# =============================================================================

class TestScoreRoute:

    @pytest.fixture(autouse=True)
    def patch_service(self, mock_model, mock_builder):
        with (
            patch("src.services.scoring_service._get_model", return_value=mock_model),
            patch("src.services.scoring_service._get_builder", return_value=mock_builder),
        ):
            yield

    def test_200_with_valid_payload(self, api_client, valid_api_payload, mock_model):
        mock_model.predict_proba.return_value = np.array([[0.9, 0.1]])
        resp = api_client.post("/score", json=valid_api_payload)
        assert resp.status_code == 200

    def test_response_schema_fields(self, api_client, valid_api_payload, mock_model):
        mock_model.predict_proba.return_value = np.array([[0.9, 0.1]])
        resp = api_client.post("/score", json=valid_api_payload)
        body = resp.json()
        assert "score" in body
        assert "model_name" in body
        assert "contributions" in body

    def test_score_in_0_1_range(self, api_client, valid_api_payload, mock_model):
        mock_model.predict_proba.return_value = np.array([[0.75, 0.25]])
        resp = api_client.post("/score", json=valid_api_payload)
        assert 0.0 <= resp.json()["score"] <= 1.0

    def test_contributions_none_by_default(self, api_client, valid_api_payload, mock_model):
        mock_model.predict_proba.return_value = np.array([[0.9, 0.1]])
        resp = api_client.post("/score", json=valid_api_payload)
        assert resp.json()["contributions"] is None

    def test_explain_true_forwarded(self, api_client, valid_api_payload, mock_model):
        """With explain=true, contributions must not be None (assuming booster exists)."""
        shap_raw = np.array([[0.1, 0.2, 0.05, 0.0]])
        booster  = MagicMock()
        booster.predict.return_value = shap_raw
        estimator = MagicMock()
        estimator.booster_ = booster
        calibrated = MagicMock()
        calibrated.estimator = estimator
        mock_model.calibrated_classifiers_ = [calibrated]
        mock_model.predict_proba.return_value = np.array([[0.8, 0.2]])

        resp = api_client.post("/score?explain=true", json=valid_api_payload)
        assert resp.status_code == 200
        assert resp.json()["contributions"] is not None

    def test_422_on_missing_required_field(self, api_client, valid_api_payload):
        payload = valid_api_payload.copy()
        del payload["transaction"]["enriched_amount_usd"]
        resp = api_client.post("/score", json=payload)
        assert resp.status_code == 422

    def test_422_on_invalid_enum_value(self, api_client, valid_api_payload):
        payload = valid_api_payload.copy()
        payload["transaction"]["channel"] = "INVALID_CHANNEL"
        resp = api_client.post("/score", json=payload)
        assert resp.status_code == 422

    def test_422_on_non_positive_amount(self, api_client, valid_api_payload):
        payload = valid_api_payload.copy()
        payload["transaction"]["enriched_amount_usd"] = -50.0
        resp = api_client.post("/score", json=payload)
        assert resp.status_code == 422

    def test_422_on_negative_txn_count(self, api_client, valid_api_payload):
        payload = valid_api_payload.copy()
        payload["card_history"]["txn_count"] = -1
        resp = api_client.post("/score", json=payload)
        assert resp.status_code == 422


# =============================================================================
# GET /schema route
# =============================================================================

class TestSchemaRoute:

    @pytest.fixture(autouse=True)
    def patch_builder(self, mock_builder):
        with patch("src.services.scoring_service._get_builder", return_value=mock_builder):
            yield

    def test_200_response(self, api_client):
        resp = api_client.get("/schema")
        assert resp.status_code == 200

    def test_returns_json(self, api_client):
        resp = api_client.get("/schema")
        assert resp.headers["content-type"].startswith("application/json")

    def test_schema_body_contains_model_name(self, api_client):
        resp = api_client.get("/schema")
        assert "model_name" in resp.json()

    def test_schema_body_contains_features(self, api_client):
        resp = api_client.get("/schema")
        body = resp.json()
        assert "features" in body
        assert isinstance(body["features"], list)