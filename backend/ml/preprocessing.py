"""
preprocessing.py
================
Training pipeline only — loads raw data, runs feature engineering,
splits chronologically, applies label-dependent encodings, and saves
train/test matrices.

This script is NOT deployed to production. The real-time feature
computation is in feature_engineering.py, which is shared with
src/services/realtime_feature_builder.py.

Dependency flow:
    feature_engineering.py  ←  preprocessing.py   (training)
    feature_engineering.py  ←  realtime_feature_builder.py  (inference)

Changelog
---------
v2 — four fixes applied:
  1. Added "transaction_country" to FINAL_DROP.
       Rationale: not in FINAL_DROP and not target-encoded, so it fell
       through to get_dummies as 6 near-identical one-hot columns. The
       comment in HIGH_CARD_COLS already documented that country-level
       fraud rates are sampling noise — now the code matches the comment.
       cross_border already captures the geographic signal.

  2. Added "is_weekend" to FINAL_DROP.
       Rationale: dow_sin / dow_cos encode day-of-week cyclically and
       contain all the information is_weekend provides as a subset.
       Keeping is_weekend added a 0.77-correlated duplicate feature that
       inflated apparent feature importance without adding new signal.

  3. Added "cardholder_present" to FINAL_DROP.
       Rationale: the column was already documented as a terminal attribute
       (not a per-transaction behavioural signal) but was not actually
       dropped. Its raw -0.34 correlation with is_fraud made it the
       dominant model split feature, causing near-perfect train metrics.
       Generator changes have reduced the correlation, but the column must
       still be excluded from the feature matrix to prevent the model from
       learning the terminal profile rather than the transaction pattern.

  4. Added min_count guard to encode_high_cardinality_post_split.
       Rationale: merchants with fewer than MIN_MERCHANT_TXN_COUNT
       transactions have unstable fraud-rate estimates (the mean of 0–2
       binary observations). These are now mapped to global_rate at
       encoding time rather than a noisy per-merchant rate. The saved
       encoding_maps["merchant_id"]["stable_ids"] set documents which
       merchants received a real rate, for debugging and monitoring.
"""

import os
import json
import pandas as pd
from pathlib import Path
from src.config import DATA_DIR
from ml.feature_engineering import (
    compute_timestamp_cyclical_features,
    compute_cross_border_flag,
    compute_card_spend_history_features,
    compute_card_transaction_velocity,
    compute_composite_fraud_signals,
    encode_categorical_features,
)

# =============================================================================
# CONFIG
# =============================================================================
DATA_PATH   = DATA_DIR / "raw" / "transactions.csv"
OUTPUT_PATH = DATA_DIR / "processed"
os.makedirs(OUTPUT_PATH, exist_ok=True)

# Minimum transaction count for a merchant to receive its own fraud-rate
# estimate rather than falling back to the global rate.
# Merchants below this threshold have too few observations for a stable mean.
MIN_MERCHANT_TXN_COUNT = 5

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
    # FIX 1: transaction_country added.
    # Not target-encoded (fraud rates are synthetic sampling noise, not real
    # country-level risk). cross_border already captures geographic mismatch.
    "transaction_country",
    "cvv2_result",              # replaced by cvv2_result_enc
    "avs_result",               # replaced by avs_result_enc
    "pan_entry_mode",           # replaced by pan_entry_mode_enc
    "authentication",           # replaced by authentication_enc
    "card_present",             # terminal attribute, not behavioural signal
    # FIX 3: cardholder_present added.
    # Terminal attribute (ISO 8583 DE 22/61), fixed per terminal type.
    # Raw correlation with is_fraud was -0.34 — dominant split feature.
    # Excluded so model learns transaction behaviour, not terminal profile.
    "cardholder_present",
    # FIX 2: is_weekend added.
    # Fully subsumed by dow_sin / dow_cos (cyclical encoding of day-of-week).
    # Keeping it created a collinear feature pair (0.77 correlation) that
    # inflated apparent feature importance without adding new signal.
    "is_weekend",
]

# High-cardinality categoricals encoded post-split using train fraud rates.
# These must also be loaded by the feature service at inference time.
HIGH_CARD_COLS = [
    "merchant_category_code",   # identifier — not ordinal, not a number
    # transaction_country excluded: fraud rate differences across the 6
    # synthetic countries are sampling noise from the random seed, not real
    # country-level risk. cross_border already captures geographic mismatch.
    # FIX 1: transaction_country is now dropped entirely in FINAL_DROP
    # rather than being encoded here, consistent with this comment.
    "merchant_id",              # fraud rate per merchant (stable merchants only)
]


# =============================================================================
# LOAD
# =============================================================================
def load_raw_transactions(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    print(f"Loaded {len(df):,} rows, {df.shape[1]} columns")
    return df


# =============================================================================
# SPLIT — chronological, never random
# =============================================================================
def split_chronologically(df: pd.DataFrame, test_frac: float = 0.20):
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
    min_count: int = MIN_MERCHANT_TXN_COUNT,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Maps each category to its historical fraud rate, computed on the train
    set only. Test set and inference use the saved map — unknown categories
    fall back to the global train fraud rate.

    FIX 4: min_count guard added.
    Categories with fewer than min_count observations in the training set
    receive the global fraud rate rather than a per-category estimate.
    This prevents noisy means from single-digit observation counts
    (particularly relevant for merchant_id, where many merchants have
    very few transactions in the training window).

    The stable_ids set is saved in encoding_maps for each column so that
    the inference service and monitoring tools can identify which categories
    are being served a real rate vs the global fallback.

    The returned encoding_maps dict must be saved alongside the model and
    loaded by realtime_feature_builder.py at startup. If it drifts from the
    model, train/serve skew occurs.
    """
    train_tmp   = X_train.copy()
    train_tmp["_label"] = y_train.values
    global_rate = float(y_train.mean())
    encoding_maps = {}

    for col in cols:
        if col not in X_train.columns:
            continue

        counts   = train_tmp.groupby(col)["_label"].count()
        raw_rate = train_tmp.groupby(col)["_label"].mean()

        # Only trust estimates from categories with enough observations.
        stable      = counts[counts >= min_count].index
        rate_map    = raw_rate[raw_rate.index.isin(stable)].to_dict()
        stable_ids  = sorted(str(s) for s in stable.tolist())

        n_total   = len(counts)
        n_stable  = len(stable)
        n_fallback = n_total - n_stable
        print(
            f"  {col}: {n_stable}/{n_total} categories stable "
            f"(≥{min_count} txns), {n_fallback} fall back to global_rate={global_rate:.4f}"
        )

        encoding_maps[col] = {
            "map":         rate_map,
            "global_rate": global_rate,
            "min_count":   min_count,
            "stable_ids":  stable_ids,
        }

        X_train[f"{col}_fraud_rate"] = X_train[col].map(rate_map).fillna(global_rate)
        X_test[f"{col}_fraud_rate"]  = X_test[col].map(rate_map).fillna(global_rate)
        X_train = X_train.drop(columns=[col])
        X_test  = X_test.drop(columns=[col])

    return X_train, X_test, encoding_maps


# =============================================================================
# FINALISE
# =============================================================================
def drop_raw_and_identifier_columns(df: pd.DataFrame) -> pd.DataFrame:
    drop = [c for c in FINAL_DROP if c in df.columns]
    return df.drop(columns=drop)


# =============================================================================
# SAVE
# =============================================================================
def save_train_test_matrices(
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
    df = load_raw_transactions(DATA_PATH)

    # --- Feature engineering ---
    # Order matters:
    #   1. compute_composite_fraud_signals must run BEFORE encode_categorical_features
    #      because it reads the raw "authentication" string column. encode_categorical_
    #      features replaces that column with authentication_enc (int), after which the
    #      composite flag computation would silently produce all-zero results.
    #   2. compute_card_spend_history_features and compute_card_transaction_velocity
    #      must run on the full unsplit DataFrame to get correct expanding-window
    #      aggregates. Splitting first would cause cold-start defaults to appear at
    #      the train/test boundary, not just at the true card first-transaction.
    df = compute_timestamp_cyclical_features(df)
    df = compute_cross_border_flag(df)
    df = compute_card_spend_history_features(df)
    df = compute_card_transaction_velocity(df)
    df = compute_composite_fraud_signals(df)   # must precede encode_categorical_features
    df = encode_categorical_features(df)

    # --- Chronological split ---
    train_df, test_df = split_chronologically(df)

    # --- Separate target ---
    y_train = train_df["is_fraud"].astype(int)
    y_test  = test_df["is_fraud"].astype(int)

    # --- Drop raw and identifier columns ---
    train_df = drop_raw_and_identifier_columns(train_df)
    test_df  = drop_raw_and_identifier_columns(test_df)

    # --- Separate features ---
    X_train = train_df.drop(columns=["is_fraud"])
    X_test  = test_df.drop(columns=["is_fraud"])

    # --- Post-split target encoding (train labels only) ---
    print("\nTarget encoding:")
    X_train, X_test, encoding_maps = encode_high_cardinality_post_split(
        X_train, X_test, y_train, HIGH_CARD_COLS
    )

    # --- Align one-hot columns (unseen category in test → 0) ---
    for col in set(X_train.columns) - set(X_test.columns):
        X_test[col] = 0
    X_test = X_test[X_train.columns]

    # --- Save ---
    save_train_test_matrices(X_train, X_test, y_train, y_test, encoding_maps, OUTPUT_PATH)

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