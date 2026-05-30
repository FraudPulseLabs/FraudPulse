"""
realtime_feature_builder.py
============================
Real-time feature construction for fraud model inference.

Location : backend/src/services/realtime_feature_builder.py

Dependency flow (read-only — never import from preprocessing.py):
    ml/feature_engineering.py  ←  src/services/realtime_feature_builder.py

Artefact paths (resolved via src/config.py):
    ml/data/processed/encoding_maps.json   — target-encoding maps saved by preprocessing.py
    ml/artefacts/feature_schema.json  — authoritative feature order + thresholds

CRITICAL CALL ORDER (mirrors preprocessing.py → run()):
    1. compute_timestamp_cyclical_features_for_single_transaction
    2. compute_cross_border_flag_for_single_transaction
    3. compute_card_spend_history_features_for_single_transaction
    4. compute_card_transaction_velocity_for_single_transaction
    5. compute_composite_fraud_signals_for_single_transaction  ← must precede encoding
    6. encode_categorical_features_for_single_transaction
    7. merchant_category_code target-encoding  (encoding_maps.json)
    8. assemble_feature_vector() in schema order

Scoring and decision logic live in src/services/scoring_service.py.
This file only builds and returns the feature dict + ordered numpy vector.

Train/serve skew prevention:
    - Encoding maps are loaded from encoding_maps.json at startup, NOT recomputed.
    - Feature order is fixed by feature_schema.json["features"].
    - Any change to feature_engineering.py requires simultaneous retraining +
      redeployment of this service.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np

from ml.feature_engineering import (
    compute_timestamp_cyclical_features_for_single_transaction,
    compute_cross_border_flag_for_single_transaction,
    compute_card_spend_history_features_for_single_transaction,
    compute_card_transaction_velocity_for_single_transaction,
    compute_composite_fraud_signals_for_single_transaction,
    encode_categorical_features_for_single_transaction,
)
from src.config import ML_ARTEFACTS_DIR, DATA_DIR

logger = logging.getLogger(__name__)

# =============================================================================
# PATHS
# =============================================================================
# src/config.py should expose:
#   ML_ARTEFACTS_DIR = BASE_DIR / "ml" / "artefacts"
# Both files are written here by ml/preprocessing.py and ml/train_lightgbm.py.
ENCODING_MAPS_PATH  = DATA_DIR / "processed" / "encoding_maps.json"
FEATURE_SCHEMA_PATH = ML_ARTEFACTS_DIR / "feature_schema.json"


# =============================================================================
# LOADER HELPERS  (called once at startup by the service class)
# =============================================================================

def _load_encoding_maps(path: Path) -> dict:
    with open(path) as f:
        maps = json.load(f)
    logger.info("Encoding maps loaded — cols=%s", list(maps.keys()))
    return maps


def _load_feature_schema(path: Path) -> dict:
    with open(path) as f:
        schema = json.load(f)
    logger.info(
        "Feature schema loaded — model=%s  features=%d",
        schema.get("model_name"), len(schema.get("features", [])),
    )
    return schema


# =============================================================================
# FEATURE BUILDER
# =============================================================================

class RealtimeFeatureBuilder:
    """
    Builds the inference feature vector for a single transaction.

    Instantiate once at application startup (e.g. in scoring_service.py or
    via FastAPI lifespan) so artefacts are loaded only once.

        builder = RealtimeFeatureBuilder()
        features, vector = builder.build(transaction, card_history)

    Scoring and decision thresholds are applied by the caller
    (scoring_service.py), not here.
    """

    def __init__(
        self,
        encoding_maps_path:  Path = ENCODING_MAPS_PATH,
        feature_schema_path: Path = FEATURE_SCHEMA_PATH,
    ) -> None:
        self._encoding_maps = _load_encoding_maps(encoding_maps_path)
        self._schema        = _load_feature_schema(feature_schema_path)
        self._feature_order: list[str] = self._schema["features"]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(
        self,
        transaction:  dict,
        card_history: dict,
    ) -> tuple[dict, np.ndarray]:
        """
        Build features and assemble the ordered inference vector.

        Parameters
        ----------
        transaction : dict
            Raw fields from the ISO 8583 authorisation message.

            Required keys
            -------------
            timestamp            : pd.Timestamp | datetime
            enriched_amount_usd  : float   (FX conversion applied upstream)
            issuing_bank_country : str
            transaction_country  : str
            cvv2_result          : str   MATCH | NOT_PROVIDED | NOT_APPLICABLE
            avs_result           : str   FULL_MATCH | PARTIAL_MATCH | NOT_PERFORMED
            pan_entry_mode       : str   CHIP | CONTACTLESS | ONLINE | MAGSTRIPE
            authentication       : str   BIOMETRICS | OTP | PIN | CVV2 | NONE
            card_type            : str   Debit | Credit | Prepaid
            channel              : str   ATM | ECOMMERCE | POS
            transaction_type     : str   purchase | withdrawal
            merchant_category_code : str

        card_history : dict
            Per-card aggregates from the card history store (Redis / Postgres).

            Required keys
            -------------
            txn_count         : int          prior transaction count (0 = cold start)
            mean_amt          : float        mean of prior enriched_amount_usd values
            std_amt           : float        std dev of prior enriched_amount_usd values
            last_ts           : float | None unix timestamp of the last transaction
            current_ts        : float        unix timestamp of this transaction
            recent_timestamps : list[float]  unix timestamps used for velocity windows

        Returns
        -------
        features : dict   feature_name → numeric value (for logging / explainability)
        vector   : np.ndarray shape (1, N) in feature_schema.json order, float32
        """
        features = self._compute_features(transaction, card_history)
        vector   = self._assemble_vector(features)
        return features, vector

    # ------------------------------------------------------------------
    # Feature computation — call order is enforced here
    # ------------------------------------------------------------------

    def _compute_features(self, transaction: dict, card_history: dict) -> dict:
        features: dict = {}

        # Step 1 — Timestamp cyclical features
        features.update(
            compute_timestamp_cyclical_features_for_single_transaction(
                transaction["timestamp"]
            )
        )

        # Step 2 — Cross-border flag
        features.update(
            compute_cross_border_flag_for_single_transaction(
                issuing_bank_country=transaction["issuing_bank_country"],
                transaction_country=transaction["transaction_country"],
            )
        )

        # Step 3 — Card spend history (expanding-window aggregates)
        features.update(
            compute_card_spend_history_features_for_single_transaction(
                enriched_amount_usd=transaction["enriched_amount_usd"],
                card_history=card_history,
            )
        )

        # Step 4 — Velocity features (rolling time windows)
        features.update(
            compute_card_transaction_velocity_for_single_transaction(
                recent_timestamps=card_history.get("recent_timestamps", []),
                current_ts=card_history["current_ts"],
            )
        )

        # Step 5 — Composite fraud signals
        # MUST precede step 6: reads the raw "authentication" string.
        # encode_categorical_features replaces it with authentication_enc (int);
        # reversing steps 5 and 6 silently zeros is_weak_auth_on_above_average_amount.
        features["authentication"] = transaction["authentication"]
        features.update(
            compute_composite_fraud_signals_for_single_transaction(features)
        )
        del features["authentication"]  # raw string not part of the model feature set

        # Step 6 — Categorical ordinal + one-hot encoding
        features.update(
            encode_categorical_features_for_single_transaction(
                cvv2_result=transaction["cvv2_result"],
                avs_result=transaction["avs_result"],
                pan_entry_mode=transaction["pan_entry_mode"],
                authentication=transaction["authentication"],
                card_type=transaction["card_type"],
                channel=transaction["channel"],
                transaction_type=transaction["transaction_type"],
            )
        )

        # Step 7 — Pass-through numeric features not derived above
        features["enriched_amount_usd"] = transaction["enriched_amount_usd"]

        # Step 8 — merchant_category_code target encoding
        # Uses the map saved by preprocessing.encode_high_cardinality_post_split().
        # Unknown / low-count MCCs fall back to global_rate, matching training.
        features["merchant_category_code_fraud_rate"] = self._encode_mcc(
            transaction["merchant_category_code"]
        )

        return features

    # ------------------------------------------------------------------
    # Target encoding
    # ------------------------------------------------------------------

    def _encode_mcc(self, mcc: str) -> float:
        """
        Map merchant_category_code to its training-set fraud rate.
        Falls back to global_rate for unseen or low-count categories,
        matching preprocessing.encode_high_cardinality_post_split().
        """
        enc         = self._encoding_maps.get("merchant_category_code", {})
        rate_map    = enc.get("map", {})
        global_rate = enc.get("global_rate", 0.0)
        return float(rate_map.get(str(mcc), global_rate))

    # ------------------------------------------------------------------
    # Vector assembly — schema order is authoritative
    # ------------------------------------------------------------------

    def _assemble_vector(self, features: dict) -> np.ndarray:
        """
        Assemble a (1, N) float32 array in the exact order defined by
        feature_schema.json. Missing features default to 0 and are logged
        as warnings so train/serve skew surfaces in monitoring.
        """
        row = []
        for name in self._feature_order:
            val = features.get(name)
            if val is None:
                logger.warning(
                    "Feature '%s' missing from built features — defaulting to 0", name
                )
                val = 0
            row.append(float(val))
        return np.array(row, dtype=np.float32).reshape(1, -1)

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------

    @property
    def feature_order(self) -> list[str]:
        """Authoritative feature list in model-input order."""
        return self._feature_order

    @property
    def feature_count(self) -> int:
        return len(self._feature_order)