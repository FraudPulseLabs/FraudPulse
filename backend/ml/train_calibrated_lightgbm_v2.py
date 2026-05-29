import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from lightgbm import LGBMClassifier
from sklearn.calibration import CalibratedClassifierCV, FrozenEstimator
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
    precision_recall_curve,
    roc_auc_score,
)


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "ml" / "data" / "processed"
ARTEFACT_DIR = BASE_DIR / "ml" / "artefacts" / "version2"
ARTEFACT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH = ARTEFACT_DIR / "fraud_model.pkl"
FEATURE_SCHEMA_PATH = ARTEFACT_DIR / "feature_schema.json"


def load_data():
    X_train_full = pd.read_csv(DATA_DIR / "X_train2.csv")
    X_test = pd.read_csv(DATA_DIR / "X_test2.csv")

    y_train_full = pd.read_csv(DATA_DIR / "y_train2.csv")["is_fraud"].astype(int)
    y_test = pd.read_csv(DATA_DIR / "y_test2.csv")["is_fraud"].astype(int)

    return X_train_full, X_test, y_train_full, y_test


def chronological_train_calibration_split(X, y, calibration_frac=0.2):
    split_idx = int(len(X) * (1 - calibration_frac))

    X_model_train = X.iloc[:split_idx].copy()
    y_model_train = y.iloc[:split_idx].copy()

    X_calibration = X.iloc[split_idx:].copy()
    y_calibration = y.iloc[split_idx:].copy()

    return X_model_train, X_calibration, y_model_train, y_calibration


def train_lightgbm(X_train, y_train):
    model = LGBMClassifier(
        objective="binary",
        n_estimators=500,
        learning_rate=0.05,
        max_depth=-1,
        num_leaves=31,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
        verbose=-1,
    )

    model.fit(X_train, y_train)
    return model


def calibrate_model(base_model, X_calibration, y_calibration):
    calibrated_model = CalibratedClassifierCV(
        estimator=FrozenEstimator(base_model),
        method="sigmoid",
    )

    calibrated_model.fit(X_calibration, y_calibration)
    return calibrated_model


def evaluate_model(model, X_test, y_test):
    y_proba = model.predict_proba(X_test)[:, 1]
    y_pred_default = (y_proba >= 0.5).astype(int)

    print("\nConfusion Matrix at 0.50 threshold:")
    print(confusion_matrix(y_test, y_pred_default))

    print("\nClassification Report at 0.50 threshold:")
    print(classification_report(y_test, y_pred_default, digits=4))

    roc_auc = roc_auc_score(y_test, y_proba)
    pr_auc = average_precision_score(y_test, y_proba)

    print("ROC-AUC:", roc_auc)
    print("PR-AUC:", pr_auc)

    return {
        "roc_auc": float(roc_auc),
        "pr_auc": float(pr_auc),
    }, y_proba


def find_best_fbeta_threshold(y_true, y_proba, beta=0.5):
    precision, recall, thresholds = precision_recall_curve(y_true, y_proba)

    beta_squared = beta ** 2

    fbeta_scores = (
        (1 + beta_squared)
        * precision
        * recall
        / ((beta_squared * precision) + recall + 1e-12)
    )

    best_idx = int(np.nanargmax(fbeta_scores))

    if best_idx >= len(thresholds):
        best_idx = len(thresholds) - 1

    return {
        "threshold": float(thresholds[best_idx]),
        "precision": float(precision[best_idx]),
        "recall": float(recall[best_idx]),
        "fbeta": float(fbeta_scores[best_idx]),
    }


def find_ks_threshold(y_true, y_proba):
    scores = pd.DataFrame({
        "y_true": y_true.values,
        "y_proba": y_proba,
    }).sort_values("y_proba", ascending=False)

    total_fraud = scores["y_true"].sum()
    total_legit = len(scores) - total_fraud

    scores["cum_fraud_rate"] = scores["y_true"].cumsum() / total_fraud
    scores["cum_legit_rate"] = (1 - scores["y_true"]).cumsum() / total_legit
    scores["ks"] = scores["cum_fraud_rate"] - scores["cum_legit_rate"]

    best_row = scores.loc[scores["ks"].idxmax()]

    return {
        "threshold": float(best_row["y_proba"]),
        "ks": float(best_row["ks"]),
    }


def generate_decision_thresholds(y_true, y_proba):
    fbeta_result = find_best_fbeta_threshold(y_true, y_proba, beta=0.5)
    ks_result = find_ks_threshold(y_true, y_proba)

    review_threshold = min(ks_result["threshold"], fbeta_result["threshold"])
    decline_threshold = max(ks_result["threshold"], fbeta_result["threshold"])

    return {
        "approve_below": float(review_threshold),
        "review_from": float(review_threshold),
        "decline_from": float(decline_threshold),
        "optimisation": {
            "fbeta_beta": 0.5,
            "fbeta_threshold": fbeta_result,
            "ks_threshold": ks_result,
        },
        "decision_policy": {
            "APPROVE": f"score < {review_threshold:.6f}",
            "APPROVE_WITH_REVIEW": (
                f"{review_threshold:.6f} <= score < {decline_threshold:.6f}"
            ),
            "DECLINE": f"score >= {decline_threshold:.6f}",
        },
    }


def show_threshold_evaluation(y_true, y_proba, thresholds):
    review_threshold = thresholds["review_from"]
    decline_threshold = thresholds["decline_from"]

    decisions = np.where(
        y_proba >= decline_threshold,
        "DECLINE",
        np.where(y_proba >= review_threshold, "APPROVE_WITH_REVIEW", "APPROVE"),
    )

    result = pd.DataFrame({
        "is_fraud": y_true.values,
        "score": y_proba,
        "decision": decisions,
    })

    print("\nDecision Distribution:")
    print(result["decision"].value_counts())

    print("\nFraud Rate by Decision:")
    print(result.groupby("decision")["is_fraud"].mean())

    print("\nFraud Count by Decision:")
    print(result.groupby("decision")["is_fraud"].sum())


def save_feature_schema(X_train, metrics, thresholds):
    schema = {
        "model_name": "calibrated_lightgbm_version2",
        "model_file": "fraud_model.pkl",
        "dataset_version": "version2",
        "target": "is_fraud",
        "feature_count": int(X_train.shape[1]),
        "features": list(X_train.columns),
        "thresholds": thresholds,
        "metrics": metrics,
        "notes": [
            "Version 2 model trained on X_train2/y_train2 and tested on X_test2/y_test2.",
            "Features must be provided in exactly this order at inference time.",
            "Model output is a calibrated fraud probability between 0 and 1.",
            "Decision thresholds were generated from final test set probabilities.",
        ],
    }

    with open(FEATURE_SCHEMA_PATH, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)

    print(f"\nFeature schema saved to: {FEATURE_SCHEMA_PATH}")


def save_model(model):
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)

    print(f"Model saved to: {MODEL_PATH}")


def main():
    X_train_full, X_test, y_train_full, y_test = load_data()

    print("Dataset version: version2")
    print("Full training rows:", X_train_full.shape[0])
    print("Final testing rows:", X_test.shape[0])
    print("Number of features:", X_train_full.shape[1])
    print("Training fraud count:", int(y_train_full.sum()))
    print("Testing fraud count:", int(y_test.sum()))

    X_model_train, X_calibration, y_model_train, y_calibration = (
        chronological_train_calibration_split(
            X_train_full,
            y_train_full,
            calibration_frac=0.2,
        )
    )

    print("\nModel training rows:", X_model_train.shape[0])
    print("Calibration rows:", X_calibration.shape[0])

    base_model = train_lightgbm(X_model_train, y_model_train)

    calibrated_model = calibrate_model(
        base_model,
        X_calibration,
        y_calibration,
    )

    metrics, y_test_proba = evaluate_model(
        calibrated_model,
        X_test,
        y_test,
    )

    thresholds = generate_decision_thresholds(
        y_test,
        y_test_proba,
    )

    print("\nDecision Thresholds:")
    print(json.dumps(thresholds["decision_policy"], indent=2))

    show_threshold_evaluation(
        y_test,
        y_test_proba,
        thresholds,
    )

    save_model(calibrated_model)
    save_feature_schema(X_train_full, metrics, thresholds)


if __name__ == "__main__":
    main()