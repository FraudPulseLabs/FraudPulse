import pandas as pd
import numpy as np

from ml.feature_engineering import (
    add_time_features,
    add_geography_features,
    add_card_features,
    add_velocity_features,
    add_risk_flags,
    encode_categoricals,
    add_card_features_single,
    add_velocity_features_single,
)


def sample_df():
    return pd.DataFrame({
        "timestamp": pd.to_datetime([
            "2025-01-01 01:00:00",
            "2025-01-01 02:00:00",
            "2025-01-01 03:00:00",
        ]),
        "card_id": ["A", "A", "A"],
        "enriched_amount_usd": [100, 200, 300],
        "issuing_bank_country": ["US", "US", "US"],
        "transaction_country": ["US", "CA", "US"],
        "authentication": ["NONE", "OTP", "CVV2"],
        "cvv2_result": ["MATCH", "MATCH", "NOT_PROVIDED"],
        "avs_result": ["FULL_MATCH", "PARTIAL_MATCH", "NOT_PERFORMED"],
        "pan_entry_mode": ["CHIP", "ONLINE", "MAGSTRIPE"],
        "card_type": ["Debit", "Credit", "Debit"],
        "channel": ["POS", "ECOMMERCE", "ATM"],
        "transaction_type": ["purchase", "purchase", "withdrawal"],
    })


def test_add_time_features():
    df = add_time_features(sample_df())

    expected_cols = [
        "hour_sin",
        "hour_cos",
        "dow_sin",
        "dow_cos",
        "is_weekend",
        "is_night",
    ]

    for col in expected_cols:
        assert col in df.columns

    assert df["is_night"].iloc[0] == 1


def test_add_geography_features():
    df = add_geography_features(sample_df())

    assert "cross_border" in df.columns
    assert df["cross_border"].tolist() == [0, 1, 0]


def test_add_card_features_no_leakage():
    df = add_card_features(sample_df())

    # First txn must have no prior history
    assert df["card_txn_count_prior"].iloc[0] == 0

    # Second txn should only see first txn
    assert df["card_avg_amount_usd_prior"].iloc[1] == 100

    # Third txn should average first two txns
    assert df["card_avg_amount_usd_prior"].iloc[2] == 150


def test_velocity_features():
    df = add_velocity_features(sample_df())

    assert "txn_count_1h" in df.columns
    assert "txn_count_24h" in df.columns

    assert df["txn_count_24h"].iloc[2] == 2


def test_risk_flags():
    df = sample_df()

    df["amount_vs_card_avg"] = [1.0, 4.0, 5.0]
    df["cross_border"] = [0, 1, 1]
    df["txn_count_1h"] = [0, 5, 1]

    df = add_risk_flags(df)

    assert df["high_amount_relative"].tolist() == [0, 1, 1]
    assert df["cross_border_high_amount"].tolist() == [0, 1, 1]
    assert df["velocity_spike_1h"].tolist() == [0, 1, 0]


def test_encode_categoricals():
    df = encode_categoricals(sample_df())

    assert "cvv2_result_enc" in df.columns
    assert "avs_result_enc" in df.columns
    assert "pan_entry_mode_enc" in df.columns
    assert "authentication_enc" in df.columns

    # One-hot checks
    assert "card_type_Debit" in df.columns
    assert "channel_POS" in df.columns


def test_card_features_single_defaults():
    result = add_card_features_single(
        enriched_amount_usd=100,
        card_history={}
    )

    assert result["card_txn_count_prior"] == 0
    assert result["seconds_since_last_txn"] == 86400.0


def test_velocity_features_single():
    result = add_velocity_features_single(
        recent_timestamps=[1000, 2000, 3000],
        current_ts=4000
    )

    assert result["txn_count_1h"] == 3
    assert result["txn_count_24h"] == 3