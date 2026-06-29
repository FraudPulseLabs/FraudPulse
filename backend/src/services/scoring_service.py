# src/services/scoring_service.py

from __future__ import annotations

import logging
import pickle
from functools import lru_cache

import numpy as np
import pandas as pd
from fastapi import HTTPException

from src.config import ML_ARTEFACTS_DIR
from src.services.realtime_feature_builder import RealtimeFeatureBuilder

logger = logging.getLogger(__name__)

_MODEL_PATH = ML_ARTEFACTS_DIR / "fraud_model_tuned.pkl"


# =============================================================================
# MODULE-LEVEL SINGLETONS  (loaded once per process)
# =============================================================================

@lru_cache(maxsize=1)
def _get_model():
    path = _MODEL_PATH
    if not path.exists():
        raise RuntimeError(f"Model artefact not found: {path}")
    with open(path, "rb") as f:
        model = pickle.load(f)
    logger.info("Fraud model loaded from %s", path)
    return model


@lru_cache(maxsize=1)
def _get_builder() -> RealtimeFeatureBuilder:
    return RealtimeFeatureBuilder()


def _to_dataframe(vector: np.ndarray, feature_order: list[str]) -> pd.DataFrame:
    """
    Wrap the numpy vector in a DataFrame with correct column names.
    Suppresses the "X does not have valid feature names" warning from sklearn
    by matching the feature names the model was fitted with.
    """
    return pd.DataFrame(vector, columns=feature_order)


# =============================================================================
# SHAP CONTRIBUTIONS
# =============================================================================

def _extract_lgbm_booster(model):
    """
    Reach inside CalibratedClassifierCV to get the underlying LightGBM estimator.

    CalibratedClassifierCV wraps one or more calibrated classifiers internally.
    Structure: model.calibrated_classifiers_[0].estimator → LGBMClassifier
    The LGBMClassifier exposes .booster_ which supports pred_contrib natively.

    Falls back to None if the structure is unexpected (e.g. different wrapper).
    """
    try:
        # CalibratedClassifierCV stores a list of _CalibratedClassifier objects
        lgbm_estimator = model.calibrated_classifiers_[0].estimator
        return lgbm_estimator.booster_   # lightgbm.Booster — supports pred_contrib
    except (AttributeError, IndexError) as exc:
        logger.warning("Could not extract LightGBM booster from model wrapper: %s", exc)
        return None

def _compute_contributions(
    model,
    df:            pd.DataFrame,
    features:      dict,
    feature_order: list[str],
) -> list[dict]:
    """
    Return per-feature SHAP values using LightGBM's native pred_contrib.

    booster_.predict() with pred_contrib=True returns shape (1, n_features + 1).
    The last column is the bias (expected log-odds across training set) — dropped.
    Remaining columns are SHAP values in feature order:
        > 0  pushed score toward fraud
        < 0  pushed score toward legitimate
    Sorted by abs(shap_value) descending so the most influential features appear first.
    """
    booster = _extract_lgbm_booster(model)
    if booster is None:
        return []

    try:
        # booster_.predict() takes a numpy array, not a DataFrame
        raw = booster.predict(df.values, pred_contrib=True)  # (1, n_features + 1)
        shap_values = raw[0, :-1]                             # drop bias column
    except Exception as exc:
        logger.warning("SHAP computation failed, skipping contributions: %s", exc)
        return []

    contributions = [
        {
            "feature":    name,
            "value":      float(features.get(name, 0)),
            "shap_value": float(shap_val),
        }
        for name, shap_val in zip(feature_order, shap_values)
    ]

    contributions.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
    return contributions


# =============================================================================
# PUBLIC API
# =============================================================================

async def score_transaction(
    transaction:  dict,
    card_history: dict,
    explain:      bool = False,
) -> dict:
    """
    Build features and return a calibrated fraud score.

    Parameters
    ----------
    transaction : dict
        Raw ISO 8583 fields. See TransactionPayload in scoring_schemas.py.
    card_history : dict
        Per-card aggregates. See CardHistoryPayload in scoring_schemas.py.
    explain : bool
        When True, include per-feature SHAP contributions sorted by absolute
        influence descending. Adds ~1–2 ms per call.

    Returns
    -------
    dict
        score          float             calibrated fraud probability [0, 1]
        model_name     str               model identifier
        contributions  list[dict] | None SHAP values (None if explain=False)
    """
    try:
        model   = _get_model()
        builder = _get_builder()
        features, vector = builder.build(transaction, card_history)

        # Wrap in DataFrame to match fitted feature names — suppresses sklearn warning
        df = _to_dataframe(vector, builder.feature_order)
        score = float(model.predict_proba(df)[0][1])

    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.exception(
            "Scoring failed for card=%s: %s",
            transaction.get("card_id", "unknown"), exc,
        )
        raise HTTPException(
            status_code=500,
            detail="Fraud scoring failed. See server logs for details.",
        )

    model_name    = builder._schema.get("model_name", "unknown")
    contributions = None

    if explain:
        contributions = _compute_contributions(
            model, df, features, builder.feature_order
        )

    logger.debug(
        "score=%.6f  card=%s  model=%s  explain=%s",
        score, transaction.get("card_id", "unknown"), model_name, explain,
    )

    return {
        "score":         score,
        "model_name":    model_name,
        "contributions": contributions,
    }


async def get_feature_schema() -> dict:
    """
    Return the full feature schema (feature list, thresholds, metrics).
    Used by the API route to expose model metadata without coupling
    the route to the artefacts directory.
    """
    return _get_builder()._schema