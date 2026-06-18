import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from lightgbm import LGBMClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import ParameterSampler


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "ml" / "data" / "processed"
ARTEFACT_DIR = BASE_DIR / "ml" / "artefacts" / "version2"
ARTEFACT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH = ARTEFACT_DIR / "fraud_model_tuned.pkl"
FEATURE_SCHEMA_PATH = ARTEFACT_DIR / "feature_schema_tuned.json"
TUNING_RESULTS_PATH = ARTEFACT_DIR / "tuning_results_v2.csv"
BEST_PARAMS_PATH = ARTEFACT_DIR / "best_params_v2.json"


def load_data():
    X_train_full = pd.read_csv(DATA_DIR / "X_train2.csv")
    X_test = pd.read_csv(DATA_DIR / "X_test2.csv")

    y_train_full = pd.read_csv(DATA_DIR / "y_train2.csv")["is_fraud"].astype(int)
    y_test = pd.read_csv(DATA_DIR / "y_test2.csv")["is_fraud"].astype(int)

    return X_train_full, X_test, y_train_full, y_test


def chronological_train_valid_calibration_split(X, y):
    """
    Time-aware split:
    first 70%  -> train candidate models
    next 15%   -> validate/tune hyperparameters
    final 15%  -> calibrate probabilities

    X_test2/y_test2 remains untouched for final evaluation.
    """
    n = len(X)

    train_end = int(n * 0.70)
    valid_end = int(n * 0.85)

    X_model_train = X.iloc[:train_end].copy()
    y_model_train = y.iloc[:train_end].copy()

    X_valid = X.iloc[train_end:valid_end].copy()
    y_valid = y.iloc[train_end:valid_end].copy()

    X_calibration = X.iloc[valid_end:].copy()
    y_calibration = y.iloc[valid_end:].copy()

    return (
        X_model_train,
        X_valid,
        X_calibration,
        y_model_train,
        y_valid,
        y_calibration,
    )


def get_param_space():
    return {
        "n_estimators": [300, 500, 800, 1000],
        "learning_rate": [0.01, 0.03, 0.05, 0.08],
        "num_leaves": [15, 31, 63],
        "max_depth": [-1, 5, 8, 12],
        "min_child_samples": [10, 20, 50, 100],
        "subsample": [0.7, 0.8, 1.0],
        "colsample_bytree": [0.7, 0.8, 1.0],
        "reg_alpha": [0.0, 0.1, 1.0],
        "reg_lambda": [0.0, 0.1, 1.0, 5.0],
    }


def train_candidate_model(X_train, y_train, params):
    model = LGBMClassifier(
        objective="binary",
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
        verbose=-1,
        **params,
    )

    model.fit(X_train, y_train)
    return model


def tune_hyperparameters(X_train, y_train, X_valid, y_valid, n_iter=40):
    param_sampler = ParameterSampler(
        get_param_space(),
        n_iter=n_iter,
        random_state=42,
    )

    results = []
    best_model = None
    best_params = None
    best_score = -1.0

    for trial, params in enumerate(param_sampler, start=1):
        print(f"\nTrial {trial}/{n_iter}")
        print(params)

        model = train_candidate_model(X_train, y_train, params)

        y_proba = model.predict_proba(X_valid)[:, 1]
        y_pred = (y_proba >= 0.5).astype(int)

        pr_auc = average_precision_score(y_valid, y_proba)
        roc_auc = roc_auc_score(y_valid, y_proba)
        precision = precision_score(y_valid, y_pred, zero_division=0)
        recall = recall_score(y_valid, y_pred, zero_division=0)
        f1 = f1_score(y_valid, y_pred, zero_division=0)

        row = {
            "trial": trial,
            "pr_auc": float(pr_auc),
            "roc_auc": float(roc_auc),
            "precision_at_0_5": float(precision),
            "recall_at_0_5": float(recall),
            "f1_at_0_5": float(f1),
            **params,
        }

        results.append(row)

        print(
            f"PR-AUC={pr_auc:.6f} | ROC-AUC={roc_auc:.6f} | "
            f"Precision={precision:.4f} | Recall={recall:.4f} | F1={f1:.4f}"
        )

        if pr_auc > best_score:
            best_score = pr_auc
            best_model = model
            best_params = params
            print("New best model found")

    results_df = pd.DataFrame(results).sort_values("pr_auc", ascending=False)
    results_df.to_csv(TUNING_RESULTS_PATH, index=False)

    with open(BEST_PARAMS_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {
                "selection_metric": "validation_pr_auc",
                "best_validation_pr_auc": float(best_score),
                "best_params": best_params,
            },
            f,
            indent=2,
        )

    print(f"\nTuning results saved to: {TUNING_RESULTS_PATH}")
    print(f"Best params saved to: {BEST_PARAMS_PATH}")

    return best_model, best_params, results_df


def calibrate_model(base_model, X_calibration, y_calibration):
    calibrated_model = CalibratedClassifierCV(
        estimator=base_model,
        method="sigmoid",
        cv="prefit",
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
    precision = precision_score(y_test, y_pred_default, zero_division=0)
    recall = recall_score(y_test, y_pred_default, zero_division=0)
    f1 = f1_score(y_test, y_pred_default, zero_division=0)

    print("ROC-AUC:", roc_auc)
    print("PR-AUC:", pr_auc)

    return {
        "accuracy": float((y_pred_default == y_test).mean()),
        "fraud_precision": float(precision),
        "fraud_recall": float(recall),
        "fraud_f1": float(f1),
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


def save_model(model):
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)

    print(f"\nTuned model saved to: {MODEL_PATH}")


def save_feature_schema(X_train, metrics, thresholds, best_params):
    schema = {
        "model_name": "tuned_calibrated_lightgbm_version2",
        "model_file": "fraud_model_tuned.pkl",
        "dataset_version": "version2",
        "target": "is_fraud",
        "feature_count": int(X_train.shape[1]),
        "features": list(X_train.columns),
        "best_params": best_params,
        "thresholds": thresholds,
        "metrics": metrics,
        "notes": [
            "Tuned Version 2 model trained on X_train2/y_train2.",
            "Hyperparameters selected using a time-aware validation split.",
            "Calibration performed using the last 15% of X_train2/y_train2.",
            "X_test2/y_test2 was used only for final evaluation.",
            "Features must be provided in exactly this order at inference time.",
        ],
    }

    with open(FEATURE_SCHEMA_PATH, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)

    print(f"Tuned feature schema saved to: {FEATURE_SCHEMA_PATH}")


def main():
    X_train_full, X_test, y_train_full, y_test = load_data()

    print("Dataset version: version2")
    print("Full training rows:", X_train_full.shape[0])
    print("Final testing rows:", X_test.shape[0])
    print("Feature count:", X_train_full.shape[1])
    print("Training fraud count:", int(y_train_full.sum()))
    print("Testing fraud count:", int(y_test.sum()))

    (
        X_model_train,
        X_valid,
        X_calibration,
        y_model_train,
        y_valid,
        y_calibration,
    ) = chronological_train_valid_calibration_split(X_train_full, y_train_full)

    print("\nModel training rows:", X_model_train.shape[0])
    print("Validation rows:", X_valid.shape[0])
    print("Calibration rows:", X_calibration.shape[0])

    best_model, best_params, _results_df = tune_hyperparameters(
        X_model_train,
        y_model_train,
        X_valid,
        y_valid,
        n_iter=40,
    )

    calibrated_model = calibrate_model(
        best_model,
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
    save_feature_schema(X_train_full, metrics, thresholds, best_params)


if __name__ == "__main__":
    main()