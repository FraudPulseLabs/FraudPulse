"""
feature_engineering.py
=======================
Shared feature computation logic used by BOTH:
  - ml/preprocessing.py        (training pipeline)
  - src/services/realtime_feature_builder.py  (real-time inference)

Rules
-----
- Every function here must be reproducible from a single transaction record
  plus data from the card history store. No function may read from the
  training dataset or require labels.
- No function imports from preprocessing.py — dependency flows one way only:
    feature_engineering  ←  preprocessing.py
    feature_engineering  ←  realtime_feature_builder.py
- Any change to logic here must be versioned and redeployed to both the
  training pipeline and the inference service simultaneously to prevent
  train/serve skew.
- Ordinal encoding maps are defined as module-level constants so the
  inference service can import them directly without re-defining them.

Inference source is documented on each function:
  ISO 8583   — value comes directly from the authorization message
  Card store  — value queried from Redis/Postgres card history store
  Derived     — computed from other already-computed features, no extra source
"""

import numpy as np
import pandas as pd

# =============================================================================
# ENCODING MAPS — module-level constants
# Imported by realtime_feature_builder.py at inference time.
# Any change here requires retraining the model.
# =============================================================================

CVV2_ORDER = {"MATCH": 0, "NOT_PROVIDED": 1, "NOT_APPLICABLE": 2}
AVS_ORDER  = {"FULL_MATCH": 0, "PARTIAL_MATCH": 1, "NOT_PERFORMED": 2}

# CHIP=safest (EMV cryptogram verified), MAGSTRIPE=riskiest (no cryptogram, clonable)
PAN_ENTRY_ORDER = {"CHIP": 0, "CONTACTLESS": 1, "ONLINE": 2, "MAGSTRIPE": 3}

# Strongest auth → weakest auth
AUTH_ORDER = {"BIOMETRICS": 0, "OTP": 1, "PIN": 2, "CVV2": 3, "NONE": 4}

# One-hot categories — defines which columns the model expects
# Used by realtime_feature_builder.py to build the correct inference vector
CARD_TYPE_CATEGORIES    = ["Debit", "Credit", "Prepaid"]
CHANNEL_CATEGORIES      = ["ATM", "ECOMMERCE", "POS"]
TXN_TYPE_CATEGORIES     = ["purchase", "withdrawal"]

# SCALING NOTE
# Numeric features are intentionally NOT scaled.
# Tree-based models (XGBoost / LightGBM / RandomForest) split on
# thresholds (e.g. amount_zscore > 2.1) — scaling changes nothing
# about where those splits land. Scaling is only required for
# distance-based models (KNN, SVM) or linear models.
# If the model type changes, add a scaling step in preprocessing.py.


# =============================================================================
# 1. TIME FEATURES
# INFERENCE SOURCE: ISO 8583 DE 12 (time) / DE 13 (date)
# =============================================================================
def compute_timestamp_cyclical_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Hour and day-of-week encoded as sine + cosine pairs to capture
    their circular nature — hour 23 and hour 0 are adjacent, not distant.
    sin(2π × hour / 24) and cos(2π × hour / 24) place each hour on a unit
    circle where every hour is equidistant from its neighbours.

    At inference: pass a single-row DataFrame with a 'timestamp' column,
    or call add_time_features_single() with a datetime object.
    """
    df = df.copy()
    hour = df["timestamp"].dt.hour
    dow  = df["timestamp"].dt.dayofweek

    df["hour_sin"]   = np.sin(2 * np.pi * hour / 24)
    df["hour_cos"]   = np.cos(2 * np.pi * hour / 24)
    df["dow_sin"]    = np.sin(2 * np.pi * dow / 7)
    df["dow_cos"]    = np.cos(2 * np.pi * dow / 7)
    df["is_weekend"] = dow.isin([5, 6]).astype(int)
    df["is_night"]   = hour.between(0, 4).astype(int)   # 00:00–04:59
    return df


def compute_timestamp_cyclical_features_for_single_transaction(timestamp: pd.Timestamp) -> dict:
    """
    Inference convenience: compute time features for a single transaction.
    Returns a dict of feature_name → value for direct insertion into the
    feature vector.
    """
    hour = timestamp.hour
    dow  = timestamp.dayofweek
    return {
        "hour_sin":   float(np.sin(2 * np.pi * hour / 24)),
        "hour_cos":   float(np.cos(2 * np.pi * hour / 24)),
        "dow_sin":    float(np.sin(2 * np.pi * dow / 7)),
        "dow_cos":    float(np.cos(2 * np.pi * dow / 7)),
        "is_weekend": int(dow in (5, 6)),
        "is_night":   int(0 <= hour <= 4),
    }


# =============================================================================
# 2. GEOGRAPHY FEATURES
# INFERENCE SOURCE: ISO 8583 DE 43 (transaction_country) +
#                   card profile (issuing_bank_country) from CMS/card store
# =============================================================================
def compute_cross_border_flag(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["cross_border"] = (
        df["issuing_bank_country"] != df["transaction_country"]
    ).astype(int)
    return df


def compute_cross_border_flag_for_single_transaction(
    issuing_bank_country: str,
    transaction_country: str,
) -> dict:
    return {
        "cross_border": int(issuing_bank_country != transaction_country)
    }


# =============================================================================
# 3. CARD BEHAVIOURAL FEATURES  (expanding window, leak-free)
# INFERENCE SOURCE: card history store (Redis/Postgres keyed by card_id)
#
# The card history store must maintain per card_id:
#   txn_count          : int   — total prior transactions
#   amount_sum         : float — sum of prior enriched_amount_usd values
#   amount_sum_sq      : float — sum of squares (for std computation)
#   last_txn_timestamp : str   — ISO timestamp of most recent transaction
#
# Store is updated ASYNCHRONOUSLY after the API response is returned.
# First-transaction defaults documented on each feature below.
# =============================================================================
def compute_card_spend_history_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Batch version for training — computes expanding-window aggregates
    using only prior rows per card (shift(1) prevents leakage).
    """
    df = df.copy().sort_values(["card_id", "timestamp"])
    grp = df.groupby("card_id")

    df["card_txn_count_prior"] = grp.cumcount()   # 0 for first transaction

    df["card_avg_amount_usd_prior"] = (
        grp["enriched_amount_usd"]
        .apply(lambda x: x.shift(1).expanding().mean())
        .reset_index(level=0, drop=True)
    )
    df["card_std_amount_usd_prior"] = (
        grp["enriched_amount_usd"]
        .apply(lambda x: x.shift(1).expanding().std())
        .reset_index(level=0, drop=True)
    )

    # Amount ratio vs card history — clamped at 20× to limit outlier influence
    # Default: 1.0 (no history available on first transaction)
    df["amount_vs_card_avg"] = (
        df["enriched_amount_usd"]
        / (df["card_avg_amount_usd_prior"].fillna(df["enriched_amount_usd"]) + 1e-6)
    ).clip(upper=20.0)

    # Z-score — clamped at ±10 to prevent extreme outliers dominating splits
    # Default: 0.0 (no history)
    df["amount_zscore"] = (
        (df["enriched_amount_usd"] - df["card_avg_amount_usd_prior"])
        / (df["card_std_amount_usd_prior"].fillna(1.0) + 1e-6)
    ).clip(-10, 10)

    # Seconds since last transaction — capped at 86 400s (24h)
    # Default: 86 400s (first transaction — assume cold start)
    df["seconds_since_last_txn"] = (
        grp["timestamp"]
        .diff()
        .dt.total_seconds()
        .fillna(86_400)
        .clip(upper=86_400)
    )

    return df


def compute_card_spend_history_features_for_single_transaction(
    enriched_amount_usd: float,
    card_history: dict,
) -> dict:
    """
    Inference version — card_history is queried from the card store.

    Expected card_history keys (all optional, defaults applied if missing):
      txn_count         : int   — number of prior transactions
      amount_mean       : float — running mean of enriched_amount_usd
      amount_std        : float — running std of enriched_amount_usd
      last_txn_ts       : float — unix timestamp of last transaction (seconds)
      current_ts        : float — unix timestamp of this transaction (seconds)
    """
    count      = card_history.get("txn_count", 0)
    mean_amt   = card_history.get("amount_mean", enriched_amount_usd)
    std_amt    = card_history.get("amount_std",  1.0)
    last_ts    = card_history.get("last_txn_ts", None)
    current_ts = card_history.get("current_ts",  None)

    amount_vs_avg = float(
        min(enriched_amount_usd / (mean_amt + 1e-6), 20.0)
    )
    amount_z = float(
        max(-10.0, min(10.0, (enriched_amount_usd - mean_amt) / (std_amt + 1e-6)))
    )

    if last_ts is not None and current_ts is not None:
        gap = min(float(current_ts - last_ts), 86_400.0)
    else:
        gap = 86_400.0   # first transaction default

    return {
        "card_txn_count_prior":       count,
        "card_avg_amount_usd_prior":  mean_amt,
        "card_std_amount_usd_prior":  std_amt,
        "amount_vs_card_avg":         amount_vs_avg,
        "amount_zscore":              amount_z,
        "seconds_since_last_txn":     gap,
    }


# =============================================================================
# 4. VELOCITY FEATURES  (rolling time windows, leak-free)
# INFERENCE SOURCE: card history store — list of recent transaction timestamps
# The store must support querying: "timestamps for card X in last N seconds"
# =============================================================================
def compute_card_transaction_velocity(df: pd.DataFrame) -> pd.DataFrame:
    """Batch version for training — counts prior transactions in rolling windows."""
    df = df.copy().sort_values(["card_id", "timestamp"]).reset_index(drop=True)

    txn_count_1h = np.zeros(len(df), dtype=int)
    txn_count_24h = np.zeros(len(df), dtype=int)

    for card_id, group in df.groupby("card_id"):
        idx = group.index
        ts = group["timestamp"].values

        for i in range(len(ts)):
            if i == 0:
                continue

            current_ts = ts[i]

            cutoff_1h = current_ts - np.timedelta64(3600, "s")
            cutoff_24h = current_ts - np.timedelta64(86400, "s")

            prior_ts = ts[:i]

            txn_count_1h[idx[i]] = np.sum(
                (prior_ts >= cutoff_1h) & (prior_ts < current_ts)
            )

            txn_count_24h[idx[i]] = np.sum(
                (prior_ts >= cutoff_24h) & (prior_ts < current_ts)
            )

    df["txn_count_1h"] = txn_count_1h
    df["txn_count_24h"] = txn_count_24h

    return df


def compute_card_transaction_velocity_for_single_transaction(
    recent_timestamps: list,
    current_ts: float,
) -> dict:
    """
    Inference version — recent_timestamps is a list of unix timestamps
    (seconds) for prior transactions on this card, queried from the store.

    current_ts is the unix timestamp of the incoming transaction.
    """
    ts_arr = np.array(recent_timestamps, dtype=float)
    return {
        "txn_count_1h":  int(np.sum(ts_arr >= current_ts - 3_600)),
        "txn_count_24h": int(np.sum(ts_arr >= current_ts - 86_400)),
    }


# =============================================================================
# 5. RISK FLAGS  (composite signals)
# INFERENCE SOURCE: derived from features already computed above
# No additional store needed — pure functions of other features.
# =============================================================================
def compute_composite_fraud_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Composite signals derived from features already computed above.
    Each flag is named to describe the specific fraud pattern it detects.
    All amount thresholds are relative to card history, not absolute USD
    values, so they generalise across different spend levels.

    Flags produced:
      is_amount_spike_vs_card_history    — amount > 3× card average
      is_cross_border_amount_spike        — cross-border + amount spike together
      is_velocity_burst_last_1h           — more than 3 txns in past hour
      is_weak_auth_on_above_average_amount— weak auth (NONE/CVV2) on 2× amount

    Note: cardholder_present intentionally excluded — it is a fixed terminal
    attribute (DE 22/DE 61), not a per-transaction behavioural signal.
    """
    df = df.copy()

    # 1 when this transaction is more than 3× the card's historical average spend
    df["is_amount_spike_vs_card_history"] = (df["amount_vs_card_avg"] > 3.0).astype(int)

    # 1 when card is used outside its home country AND amount is a spike
    df["is_cross_border_amount_spike"] = (
        (df["cross_border"] == 1) & (df["is_amount_spike_vs_card_history"] == 1)
    ).astype(int)

    # 1 when more than 3 transactions have occurred on this card in the past hour
    df["is_velocity_burst_last_1h"] = (df["txn_count_1h"] > 3).astype(int)

    # 1 when authentication is weak (NONE or CVV2) on a transaction
    # that is more than 2× the card's historical average — elevated risk combination
    df["is_weak_auth_on_above_average_amount"] = (
        df["authentication"].isin(["NONE", "CVV2"]) &
        (df["amount_vs_card_avg"] > 2.0)
    ).astype(int)

    return df


def compute_composite_fraud_signals_for_single_transaction(features: dict) -> dict:
    """
    Inference version — pass the already-computed feature dict and
    this appends the derived risk flag values.
    """
    is_amount_spike = int(features.get("amount_vs_card_avg", 1.0) > 3.0)
    return {
        "is_amount_spike_vs_card_history":    is_amount_spike,
        "is_cross_border_amount_spike":        int(
            features.get("cross_border", 0) == 1 and is_amount_spike == 1
        ),
        "is_velocity_burst_last_1h":           int(features.get("txn_count_1h", 0) > 3),
        "is_weak_auth_on_above_average_amount": int(
            features.get("authentication", "") in ("NONE", "CVV2")
            and features.get("amount_vs_card_avg", 1.0) > 2.0
        ),
    }


# =============================================================================
# 6. CATEGORICAL ENCODING  (ordinal + one-hot)
# INFERENCE SOURCE: ISO 8583 message fields
# Assumption: tree-based model (XGBoost/LightGBM/RandomForest).
# If switching to a linear model, replace ordinal encodings with one-hot.
# =============================================================================
def encode_categorical_features(df: pd.DataFrame) -> pd.DataFrame:
    """Batch version for training."""
    df = df.copy()

    df["cvv2_result_enc"]     = df["cvv2_result"].map(CVV2_ORDER).fillna(2).astype(int)
    df["avs_result_enc"]      = df["avs_result"].map(AVS_ORDER).fillna(2).astype(int)
    df["pan_entry_mode_enc"]  = df["pan_entry_mode"].map(PAN_ENTRY_ORDER).fillna(2).astype(int)
    df["authentication_enc"]  = df["authentication"].map(AUTH_ORDER).fillna(4).astype(int)

    ohe_cols = ["card_type", "channel", "transaction_type"]
    df = pd.get_dummies(df, columns=ohe_cols, drop_first=False, dtype=int)

    return df


def encode_categorical_features_for_single_transaction(
    cvv2_result: str,
    avs_result: str,
    pan_entry_mode: str,
    authentication: str,
    card_type: str,
    channel: str,
    transaction_type: str,
) -> dict:
    """
    Inference version — encodes a single transaction's categorical fields.
    One-hot columns use the fixed category lists defined at module level
    so the output vector always has the same columns in the same order.
    """
    features = {
        "cvv2_result_enc":    CVV2_ORDER.get(cvv2_result, 2),
        "avs_result_enc":     AVS_ORDER.get(avs_result, 2),
        "pan_entry_mode_enc": PAN_ENTRY_ORDER.get(pan_entry_mode, 2),
        "authentication_enc": AUTH_ORDER.get(authentication, 4),
    }

    for cat in CARD_TYPE_CATEGORIES:
        features[f"card_type_{cat}"] = int(card_type == cat)
    for cat in CHANNEL_CATEGORIES:
        features[f"channel_{cat}"] = int(channel == cat)
    for cat in TXN_TYPE_CATEGORIES:
        features[f"transaction_type_{cat}"] = int(transaction_type == cat)

    return features