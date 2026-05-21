import json
import pickle
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "processed"
ARTEFACT_DIR = BASE_DIR / "ml" / "artefacts"

MODEL_PATH = ARTEFACT_DIR / "fraud_model.pkl"
FEATURE_SCHEMA_PATH = ARTEFACT_DIR / "feature_schema.json"


def load_model():
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)


def load_feature_schema():
    with open(FEATURE_SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_sample():
    X_test = pd.read_csv(DATA_DIR / "X_test.csv")
    y_test = pd.read_csv(DATA_DIR / "y_test.csv")["is_fraud"].astype(int)

    fraud_indices = y_test[y_test == 1000].index

    if len(fraud_indices) == 0:
        sample_idx = 0
    else:
        sample_idx = fraud_indices[0]

    sample = X_test.iloc[[sample_idx]].copy()
    actual_label = int(y_test.iloc[sample_idx])

    return sample, actual_label


def apply_decision(score, thresholds):
    if score >= thresholds["decline_from"]:
        return "DECLINE"

    if score >= thresholds["review_from"]:
        return "APPROVE_WITH_REVIEW"

    return "APPROVE"


def validate_features(sample, expected_features):
    missing_features = [feature for feature in expected_features if feature not in sample.columns]
    extra_features = [feature for feature in sample.columns if feature not in expected_features]

    if missing_features:
        raise ValueError(f"Missing required features: {missing_features}")

    if extra_features:
        print(f"Warning: extra features ignored: {extra_features}")

    return sample[expected_features]


def main():
    model = load_model()
    schema = load_feature_schema()

    expected_features = schema["features"]
    thresholds = schema["thresholds"]

    sample, actual_label = load_sample()
    sample = validate_features(sample, expected_features)

    fraud_score = float(model.predict_proba(sample)[0, 1])
    decision = apply_decision(fraud_score, thresholds)

    print("Loaded model:", schema.get("model_name", "unknown"))
    print("Model file:", schema.get("model_file", MODEL_PATH.name))
    print("Feature count:", len(expected_features))

    print("\nSample inference result:")
    print("Actual label:", actual_label)
    print("Fraud score:", round(fraud_score, 6))
    print("Decision:", decision)

    print("\nDecision thresholds:")
    print("APPROVE:", f"score < {thresholds['review_from']:.6f}")
    print(
        "APPROVE_WITH_REVIEW:",
        f"{thresholds['review_from']:.6f} <= score < {thresholds['decline_from']:.6f}",
    )
    print("DECLINE:", f"score >= {thresholds['decline_from']:.6f}")


if __name__ == "__main__":
    main()