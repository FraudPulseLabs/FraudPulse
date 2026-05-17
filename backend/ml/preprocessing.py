"""
preprocessing.py
================
Training pipeline only — loads raw data, runs feature engineering,
splits chronologically, applies label-dependent encodings, and saves
train/test matrices.

This script is NOT deployed to production. The real-time feature
computation is in feature_engineering.py, which is shared with
src/services/feature_service.py.

Dependency flow:
    feature_engineering.py  ←  preprocessing.py   (training)
    feature_engineering.py  ←  feature_service.py  (inference)
"""

import os
import json
import pandas as pd
from pathlib import Path
from src.config import DATA_DIR
from ml.feature_engineering import (
    add_time_features,
    add_geography_features,
    add_card_features,
    add_velocity_features,
    add_risk_flags,
    encode_categoricals,
)

# =============================================================================
# CONFIG
# =============================================================================
DATA_PATH   = DATA_DIR / "raw" / "transactions.csv"
OUTPUT_PATH = DATA_DIR / "processed"
os.makedirs(OUTPUT_PATH, exist_ok=True)

# Columns dropped after feature engineering.
# Raw fields are replaced by engineered versions.
# Identifiers have no predictive signal once card-level features are computed.
FINAL_DROP = [
    "transaction_id", "card_id", "merchant_id", "terminal_id",
    "timestamp",
    "transaction_amount",       # replaced by enriched_amount_usd
    "transaction_currency",     # signal captured by enriched_amount_usd
    "transaction_city",         # too granular, no model signal
    "issuing_bank_country",     # signal captured by cross_border
    "cvv2_result",              # replaced by cvv2_result_enc
    "avs_result",               # replaced by avs_result_enc
    "pan_entry_mode",           # replaced by pan_entry_mode_enc
    "authentication",           # replaced by authentication_enc
    "card_present",             # terminal attribute, not behavioural signal
    "cardholder_present",       # terminal attribute (fixed per terminal type)
]

# High-cardinality categoricals encoded post-split using train fraud rates.
# These must also be loaded by the feature service at inference time.
HIGH_CARD_COLS = [
    "merchant_category_code",   # identifier — not ordinal, not a number
    "transaction_country",      # encode as fraud rate, not country identity
    "merchant_id",              # fraud rate per merchant
]


# =============================================================================
# LOAD
# =============================================================================
def load(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    print(f"Loaded {len(df):,} rows, {df.shape[1]} columns")
    return df


# =============================================================================
# SPLIT — chronological, never random
# =============================================================================
def time_split(df: pd.DataFrame, test_frac: float = 0.20):
    """
    Split at the chronological quantile — model trains on past data and
    evaluates on future data, mirroring production deployment.
    Random splits are prohibited: they leak future fraud patterns into training.
    """
    split_ts = df["timestamp"].quantile(1 - test_frac, interpolation="nearest")
    train    = df[df["timestamp"] <= split_ts].copy()
    test     = df[df["timestamp"] >  split_ts].copy()
    print(f"Split at {split_ts}  |  train={len(train):,}  test={len(test):,}")
    return train, test


# =============================================================================
# POST-SPLIT TARGET ENCODING
# =============================================================================
def encode_high_cardinality_post_split(
    X_train: pd.DataFrame,
    X_test:  pd.DataFrame,
    y_train: pd.Series,
    cols: list,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Maps each category to its historical fraud rate, computed on the train
    set only. Test set and inference use the saved map — unknown categories
    fall back to the global train fraud rate.

    The returned encoding_maps dict must be saved alongside the model and
    loaded by feature_service.py at startup. If it drifts from the model,
    train/serve skew occurs.
    """
    train_tmp   = X_train.copy()
    train_tmp["_label"] = y_train.values
    global_rate = float(y_train.mean())
    encoding_maps = {}

    for col in cols:
        if col not in X_train.columns:
            continue
        rate_map = train_tmp.groupby(col)["_label"].mean().to_dict()
        encoding_maps[col] = {"map": rate_map, "global_rate": global_rate}

        X_train[f"{col}_fraud_rate"] = X_train[col].map(rate_map).fillna(global_rate)
        X_test[f"{col}_fraud_rate"]  = X_test[col].map(rate_map).fillna(global_rate)
        X_train = X_train.drop(columns=[col])
        X_test  = X_test.drop(columns=[col])

    return X_train, X_test, encoding_maps


# =============================================================================
# FINALISE
# =============================================================================
def finalise(df: pd.DataFrame) -> pd.DataFrame:
    drop = [c for c in FINAL_DROP if c in df.columns]
    return df.drop(columns=drop)


# =============================================================================
# SAVE
# =============================================================================
def save_outputs(
    X_train: pd.DataFrame,
    X_test:  pd.DataFrame,
    y_train: pd.Series,
    y_test:  pd.Series,
    encoding_maps: dict,
    output_path: str,
) -> None:
    X_train.to_csv(f"{output_path}/X_train.csv", index=False)
    X_test.to_csv(f"{output_path}/X_test.csv",   index=False)
    y_train.to_csv(f"{output_path}/y_train.csv",  index=False)
    y_test.to_csv(f"{output_path}/y_test.csv",    index=False)

    maps_path = f"{output_path}/encoding_maps.json"
    with open(maps_path, "w") as f:
        json.dump(encoding_maps, f, indent=2)
    print(f"Encoding maps → {maps_path}")
    print("Saved: X_train, X_test, y_train, y_test")


# =============================================================================
# MAIN
# =============================================================================
def run():
    # --- Load ---
    df = load(DATA_PATH)

    # --- Feature engineering (shared with inference via feature_engineering.py) ---
    df = add_time_features(df)
    df = add_geography_features(df)
    df = add_card_features(df)
    df = add_velocity_features(df)
    df = add_risk_flags(df)
    df = encode_categoricals(df)

    # --- Chronological split ---
    train_df, test_df = time_split(df)

    # --- Separate target ---
    y_train = train_df["is_fraud"].astype(int)
    y_test  = test_df["is_fraud"].astype(int)

    # --- Drop raw and identifier columns ---
    train_df = finalise(train_df)
    test_df  = finalise(test_df)

    # --- Separate features ---
    X_train = train_df.drop(columns=["is_fraud"])
    X_test  = test_df.drop(columns=["is_fraud"])

    # --- Post-split target encoding (train labels only) ---
    X_train, X_test, encoding_maps = encode_high_cardinality_post_split(
        X_train, X_test, y_train, HIGH_CARD_COLS
    )

    # --- Align one-hot columns (unseen category in test → 0) ---
    for col in set(X_train.columns) - set(X_test.columns):
        X_test[col] = 0
    X_test = X_test[X_train.columns]

    # --- Save ---
    save_outputs(X_train, X_test, y_train, y_test, encoding_maps, OUTPUT_PATH)

    print("\n--- PREPROCESSING SUMMARY ---")
    print(f"Train : {X_train.shape[0]:,} rows × {X_train.shape[1]} features")
    print(f"Test  : {X_test.shape[0]:,} rows × {X_test.shape[1]} features")
    print(f"Fraud%  train={y_train.mean():.2%}  test={y_test.mean():.2%}")
    print(f"\nFeatures ({X_train.shape[1]}):")
    for col in X_train.columns:
        print(f"  {col}")
    print(f"\nOutputs → {OUTPUT_PATH}")


if __name__ == "__main__":
    run()