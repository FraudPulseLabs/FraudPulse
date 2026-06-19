"""
tests/unit/test_feature_builder.py
====================================
pytest suite for RealtimeFeatureBuilder.

Run from the backend/ directory:
    pytest tests/unit/test_feature_builder.py -v

Coverage:
    - Artefact loading (encoding maps + feature schema)
    - Feature dict completeness and numeric safety (NaN / Inf)
    - Vector shape, dtype, and ordering
    - Cold-start card edge case
    - Cross-border flag
    - Velocity burst
    - MCC target-encoding (known, unknown, empty)
    - Missing feature defaulting + warning log
    - Step-5/6 ordering bug guard (is_weak_auth_on_above_average_amount)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.services.realtime_feature_builder import RealtimeFeatureBuilder


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def builder() -> RealtimeFeatureBuilder:
    """Single builder instance shared across the module — artefacts load once."""
    return RealtimeFeatureBuilder()


@pytest.fixture
def domestic_transaction() -> dict:
    return {
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
def returning_card_history() -> dict:
    return {
        "txn_count":          42,
        "mean_amt":           78.50,
        "std_amt":            22.10,
        "last_ts":            1718450000.0,
        "current_ts":         1718453600.0,
        "recent_timestamps":  [1718450000.0, 1718449000.0],
    }


@pytest.fixture
def cold_start_transaction() -> dict:
    return {
        "timestamp":              datetime(2024, 6, 15, 2, 15, tzinfo=timezone.utc),
        "enriched_amount_usd":    1200.00,
        "issuing_bank_country":   "US",
        "transaction_country":    "US",
        "cvv2_result":            "MATCH",
        "avs_result":             "FULL_MATCH",
        "pan_entry_mode":         "ONLINE",
        "authentication":         "CVV2",
        "card_type":              "Credit",
        "channel":                "ECOMMERCE",
        "transaction_type":       "purchase",
        "merchant_category_code": "5999",
    }


@pytest.fixture
def cold_start_history() -> dict:
    return {
        "txn_count":         0,
        "mean_amt":          0.0,
        "std_amt":           0.0,
        "last_ts":           None,
        "current_ts":        1718410500.0,
        "recent_timestamps": [],
    }


@pytest.fixture
def cross_border_transaction() -> dict:
    return {
        "timestamp":              datetime(2024, 6, 15, 22, 45, tzinfo=timezone.utc),
        "enriched_amount_usd":    430.00,
        "issuing_bank_country":   "US",
        "transaction_country":    "NG",
        "cvv2_result":            "NOT_PROVIDED",
        "avs_result":             "NOT_PERFORMED",
        "pan_entry_mode":         "MAGSTRIPE",
        "authentication":         "NONE",
        "card_type":              "Credit",
        "channel":                "ATM",
        "transaction_type":       "withdrawal",
        "merchant_category_code": "9999",
    }


@pytest.fixture
def velocity_burst_history() -> dict:
    return {
        "txn_count":         8,
        "mean_amt":          60.00,
        "std_amt":           15.00,
        "last_ts":           1718495800.0,
        "current_ts":        1718495900.0,
        "recent_timestamps": [
            1718493000.0,
            1718493500.0,
            1718494000.0,
            1718494800.0,
            1718495200.0,
            1718495800.0,
        ],
    }


# =============================================================================
# ARTEFACT LOADING
# =============================================================================

class TestArtefactLoading:

    def test_builder_loads_without_error(self, builder):
        assert builder is not None

    def test_feature_order_is_populated(self, builder):
        assert len(builder.feature_order) > 0

    def test_feature_count_matches_order(self, builder):
        assert builder.feature_count == len(builder.feature_order)

    def test_encoding_maps_loaded(self, builder):
        assert isinstance(builder._encoding_maps, dict)
        assert len(builder._encoding_maps) > 0

    def test_schema_has_model_name(self, builder):
        assert "model_name" in builder._schema
        assert builder._schema["model_name"]  # non-empty string

    def test_schema_has_features_list(self, builder):
        assert "features" in builder._schema
        assert isinstance(builder._schema["features"], list)

    def test_raises_on_missing_encoding_maps(self, tmp_path):
        schema_path = tmp_path / "feature_schema.json"
        import json
        schema_path.write_text(json.dumps({"model_name": "test", "features": []}))
        with pytest.raises(FileNotFoundError):
            RealtimeFeatureBuilder(
                encoding_maps_path=tmp_path / "nonexistent.json",
                feature_schema_path=schema_path,
            )

    def test_raises_on_missing_feature_schema(self, tmp_path):
        enc_path = tmp_path / "encoding_maps.json"
        enc_path.write_text("{}")
        with pytest.raises(FileNotFoundError):
            RealtimeFeatureBuilder(
                encoding_maps_path=enc_path,
                feature_schema_path=tmp_path / "nonexistent.json",
            )


# =============================================================================
# VECTOR SHAPE + DTYPE
# =============================================================================

class TestVectorProperties:

    def test_vector_shape(self, builder, domestic_transaction, returning_card_history):
        _, vector = builder.build(domestic_transaction, returning_card_history)
        assert vector.shape == (1, builder.feature_count)

    def test_vector_dtype_float32(self, builder, domestic_transaction, returning_card_history):
        _, vector = builder.build(domestic_transaction, returning_card_history)
        assert vector.dtype == np.float32

    def test_no_nans_in_vector(self, builder, domestic_transaction, returning_card_history):
        _, vector = builder.build(domestic_transaction, returning_card_history)
        assert not np.any(np.isnan(vector)), "NaN found in feature vector"

    def test_no_infs_in_vector(self, builder, domestic_transaction, returning_card_history):
        _, vector = builder.build(domestic_transaction, returning_card_history)
        assert not np.any(np.isinf(vector)), "Inf found in feature vector"

    def test_feature_dict_completeness(self, builder, domestic_transaction, returning_card_history):
        """Every name in feature_order must be present in the returned feature dict."""
        features, _ = builder.build(domestic_transaction, returning_card_history)
        missing = [name for name in builder.feature_order if name not in features]
        assert not missing, f"Missing features in dict: {missing}"

    def test_vector_column_order_matches_schema(self, builder, domestic_transaction, returning_card_history):
        """
        For a feature that is 1.0 (cross_border_flag on a cross-border txn),
        confirm its position in the vector matches its position in feature_order.
        """
        features, vector = builder.build(domestic_transaction, returning_card_history)
        for i, name in enumerate(builder.feature_order):
            expected = float(features.get(name, 0))
            actual   = float(vector[0, i])
            assert actual == pytest.approx(expected, abs=1e-6), (
                f"Column {i} ({name}): vector={actual} ≠ features={expected}"
            )


# =============================================================================
# COLD-START CARD
# =============================================================================

class TestColdStartCard:

    def test_no_nans_on_cold_start(self, builder, cold_start_transaction, cold_start_history):
        _, vector = builder.build(cold_start_transaction, cold_start_history)
        assert not np.any(np.isnan(vector))

    def test_no_infs_on_cold_start(self, builder, cold_start_transaction, cold_start_history):
        """amount_zscore must not be Inf when std_amt=0 (cold start)."""
        _, vector = builder.build(cold_start_transaction, cold_start_history)
        assert not np.any(np.isinf(vector))

    def test_vector_shape_on_cold_start(self, builder, cold_start_transaction, cold_start_history):
        _, vector = builder.build(cold_start_transaction, cold_start_history)
        assert vector.shape == (1, builder.feature_count)

    def test_cold_start_zero_txn_count(self, builder, cold_start_transaction, cold_start_history):
        """txn_count=0 should feed through; downstream features must handle it gracefully."""
        features, _ = builder.build(cold_start_transaction, cold_start_history)
        # feature_engineering is expected to map txn_count=0 without crashing
        # (exact feature name may vary; we just assert no exception above)
        assert features is not None


# =============================================================================
# HELPERS
# =============================================================================

def _cross_border_key(features: dict) -> str | None:
    """
    Return the actual feature key used for the cross-border flag.
    We search for any key containing 'cross' or 'border' (case-insensitive)
    rather than hard-coding a name that may differ across model versions.
    """
    for k in features:
        if "cross" in k.lower() or "border" in k.lower():
            return k
    return None


# =============================================================================
# CROSS-BORDER FLAG
# =============================================================================

class TestCrossBorderFlag:

    def test_cross_border_flag_set_when_countries_differ(
        self, builder, cross_border_transaction, velocity_burst_history
    ):
        features, _ = builder.build(cross_border_transaction, velocity_burst_history)
        key = _cross_border_key(features)
        assert key is not None, (
            f"No cross-border feature found in features dict. Keys: {list(features)}"
        )
        assert features[key] == 1, (
            f"Expected {key}=1 for US→NG transaction, got {features[key]}"
        )

    def test_cross_border_flag_clear_when_same_country(
        self, builder, domestic_transaction, returning_card_history
    ):
        features, _ = builder.build(domestic_transaction, returning_card_history)
        key = _cross_border_key(features)
        assert key is not None, (
            f"No cross-border feature found in features dict. Keys: {list(features)}"
        )
        assert features[key] == 0, (
            f"Expected {key}=0 for domestic transaction, got {features[key]}"
        )


# =============================================================================
# VELOCITY FEATURES
# =============================================================================

# Anchor for velocity tests: both low- and high-velocity histories share the
# same current_ts so window cutoffs are identical and the comparison is fair.
_VELOCITY_BASE_TS = 1718500000.0   # arbitrary fixed "now"


class TestVelocityFeatures:

    def test_velocity_burst_produces_finite_features(
        self, builder, cross_border_transaction, velocity_burst_history
    ):
        _, vector = builder.build(cross_border_transaction, velocity_burst_history)
        assert not np.any(np.isnan(vector))
        assert not np.any(np.isinf(vector))

    def test_no_recent_timestamps_does_not_crash(
        self, builder, domestic_transaction, returning_card_history
    ):
        """recent_timestamps=[] is valid (new window, no prior txns in range)."""
        history = {**returning_card_history, "recent_timestamps": []}
        _, vector = builder.build(domestic_transaction, history)
        assert vector.shape == (1, builder.feature_count)

    def test_velocity_higher_with_burst(self, builder, domestic_transaction):
        """
        Both histories share the same current_ts so window cutoffs are identical.
        The burst history has 6 timestamps within the last hour; the sparse history
        has only 2, spread over a longer range.  The sum of all velocity-window
        counts must be strictly higher for the burst card.
        """
        sparse_history = {
            "txn_count":         10,
            "mean_amt":          80.0,
            "std_amt":           20.0,
            "last_ts":           _VELOCITY_BASE_TS - 3600.0,
            "current_ts":        _VELOCITY_BASE_TS,
            # 2 txns, both > 1 h ago → contribute to 6h/24h windows only
            "recent_timestamps": [
                _VELOCITY_BASE_TS - 7200.0,
                _VELOCITY_BASE_TS - 3600.0,
            ],
        }
        burst_history = {
            "txn_count":         10,
            "mean_amt":          80.0,
            "std_amt":           20.0,
            "last_ts":           _VELOCITY_BASE_TS - 100.0,
            "current_ts":        _VELOCITY_BASE_TS,
            # 6 txns all within the last hour
            "recent_timestamps": [
                _VELOCITY_BASE_TS - 3000.0,
                _VELOCITY_BASE_TS - 2500.0,
                _VELOCITY_BASE_TS - 2000.0,
                _VELOCITY_BASE_TS - 1200.0,
                _VELOCITY_BASE_TS - 800.0,
                _VELOCITY_BASE_TS - 100.0,
            ],
        }

        features_low,  _ = builder.build(domestic_transaction, sparse_history)
        features_high, _ = builder.build(domestic_transaction, burst_history)

        vel_keys = [k for k in features_low if "velocity" in k or "txn_count_" in k]
        if not vel_keys:
            pytest.skip("No velocity feature key found — adjust key search pattern")

        low_total  = sum(features_low[k]  for k in vel_keys)
        high_total = sum(features_high[k] for k in vel_keys)
        assert high_total > low_total, (
            f"Burst history should produce higher velocity totals. "
            f"burst={high_total}, sparse={low_total}, keys={vel_keys}"
        )


# =============================================================================
# MCC TARGET ENCODING
# =============================================================================

class TestMccEncoding:

    def test_known_mcc_returns_map_value(self, builder):
        enc         = builder._encoding_maps.get("merchant_category_code", {})
        rate_map    = enc.get("map", {})
        global_rate = enc.get("global_rate", 0.0)

        known_mcc = next(iter(rate_map), None)
        if known_mcc is None:
            pytest.skip("Encoding map is empty — cannot test known MCC")

        result = builder._encode_mcc(known_mcc)
        assert result == pytest.approx(rate_map[known_mcc])
        assert result != global_rate or rate_map[known_mcc] == global_rate

    def test_unknown_mcc_returns_global_rate(self, builder):
        enc         = builder._encoding_maps.get("merchant_category_code", {})
        global_rate = enc.get("global_rate", 0.0)
        result      = builder._encode_mcc("0000")
        assert result == pytest.approx(global_rate)

    def test_empty_mcc_returns_global_rate(self, builder):
        enc         = builder._encoding_maps.get("merchant_category_code", {})
        global_rate = enc.get("global_rate", 0.0)
        result      = builder._encode_mcc("")
        assert result == pytest.approx(global_rate)

    def test_mcc_encoding_is_float(self, builder):
        result = builder._encode_mcc("5411")
        assert isinstance(result, float)

    def test_mcc_encoding_range(self, builder):
        """Fraud rates must be in [0, 1]."""
        for mcc in ["5411", "0000", "", "9999"]:
            result = builder._encode_mcc(mcc)
            assert 0.0 <= result <= 1.0, f"MCC {mcc!r} produced out-of-range rate: {result}"


# =============================================================================
# MISSING FEATURE DEFAULTING
# =============================================================================

class TestMissingFeatureDefaulting:

    def test_missing_feature_defaults_to_zero_with_warning(
        self, builder, domestic_transaction, returning_card_history, caplog
    ):
        """
        If a feature present in feature_schema.json is absent from the built
        features dict, _assemble_vector must default to 0 and emit a WARNING.
        """
        original_compute = builder._compute_features

        def patched_compute(transaction, card_history):
            features = original_compute(transaction, card_history)
            # Remove the first feature from the schema to trigger the default path
            first_feature = builder.feature_order[0]
            features.pop(first_feature, None)
            return features

        with patch.object(builder, "_compute_features", side_effect=patched_compute):
            with caplog.at_level(logging.WARNING):
                _, vector = builder.build(domestic_transaction, returning_card_history)

        first_feature = builder.feature_order[0]
        assert any(
            first_feature in record.message
            for record in caplog.records
            if record.levelno == logging.WARNING
        ), f"Expected WARNING mentioning '{first_feature}'"

        # The defaulted position should be 0.0
        assert vector[0, 0] == pytest.approx(0.0)


# =============================================================================
# COMPOSITE FRAUD SIGNAL — STEP ORDER GUARD
# =============================================================================

class TestCompositeSignalStepOrder:

    def test_is_weak_auth_on_above_average_amount_present(
        self, builder, domestic_transaction, returning_card_history
    ):
        """
        is_weak_auth_on_above_average_amount is computed in step 5 using the raw
        'authentication' string.  Step 6 then replaces it with authentication_enc.
        If steps are reversed this feature silently becomes 0 — assert it is built.
        """
        features, _ = builder.build(domestic_transaction, returning_card_history)
        assert "is_weak_auth_on_above_average_amount" in features, (
            "Composite feature missing — possible step-5/6 ordering regression"
        )

    def test_raw_authentication_string_not_in_final_features(
        self, builder, domestic_transaction, returning_card_history
    ):
        """
        The raw 'authentication' string is a temporary scratchpad value;
        it must be deleted before the feature dict is returned.
        """
        features, _ = builder.build(domestic_transaction, returning_card_history)
        assert "authentication" not in features, (
            "'authentication' raw string leaked into final feature dict"
        )

    def test_weak_auth_signal_is_1_for_none_auth_above_average(self, builder):
        """
        NONE authentication on an amount well above the card's mean should
        set is_weak_auth_on_above_average_amount = 1.
        """
        txn = {
            "timestamp":              datetime(2024, 6, 15, 14, 30, tzinfo=timezone.utc),
            "enriched_amount_usd":    500.00,   # >> mean_amt=60
            "issuing_bank_country":   "US",
            "transaction_country":    "NG",
            "cvv2_result":            "NOT_PROVIDED",
            "avs_result":             "NOT_PERFORMED",
            "pan_entry_mode":         "MAGSTRIPE",
            "authentication":         "NONE",   # weak
            "card_type":              "Credit",
            "channel":                "ATM",
            "transaction_type":       "withdrawal",
            "merchant_category_code": "5411",
        }
        history = {
            "txn_count":         20,
            "mean_amt":          60.00,
            "std_amt":           15.00,
            "last_ts":           1718450000.0,
            "current_ts":        1718453600.0,
            "recent_timestamps": [],
        }
        features, _ = builder.build(txn, history)
        assert features.get("is_weak_auth_on_above_average_amount") == 1


# =============================================================================
# ENRICHED AMOUNT PASS-THROUGH
# =============================================================================

class TestPassthroughFeatures:

    def test_enriched_amount_usd_present(self, builder, domestic_transaction, returning_card_history):
        features, _ = builder.build(domestic_transaction, returning_card_history)
        assert "enriched_amount_usd" in features

    def test_enriched_amount_usd_value_unchanged(
        self, builder, domestic_transaction, returning_card_history
    ):
        features, _ = builder.build(domestic_transaction, returning_card_history)
        assert features["enriched_amount_usd"] == pytest.approx(
            domestic_transaction["enriched_amount_usd"]
        )


# =============================================================================
# INTROSPECTION HELPERS
# =============================================================================

class TestIntrospectionHelpers:

    def test_feature_order_property_returns_list(self, builder):
        assert isinstance(builder.feature_order, list)

    def test_feature_count_property_is_int(self, builder):
        assert isinstance(builder.feature_count, int)
        assert builder.feature_count > 0

    def test_feature_order_and_count_consistent(self, builder):
        assert builder.feature_count == len(builder.feature_order)

    def test_feature_order_items_are_strings(self, builder):
        assert all(isinstance(f, str) for f in builder.feature_order)

    def test_feature_order_has_no_duplicates(self, builder):
        assert len(builder.feature_order) == len(set(builder.feature_order))