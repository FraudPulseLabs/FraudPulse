import joblib
import pandas as pd

from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    average_precision_score,
)


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "processed"
MODEL_DIR = BASE_DIR / "ml" / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)


def load_data():
    X_train = pd.read_csv(DATA_DIR / "X_train.csv")
    X_test = pd.read_csv(DATA_DIR / "X_test.csv")
    y_train = pd.read_csv(DATA_DIR / "y_train.csv")["is_fraud"]
    y_test = pd.read_csv(DATA_DIR / "y_test.csv")["is_fraud"]

    return X_train, X_test, y_train, y_test


def train_model(X_train, y_train):
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=None,
        min_samples_split=2,
        min_samples_leaf=1,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )

    model.fit(X_train, y_train)
    return model


def evaluate_model(model, X_test, y_test):
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    print("\nConfusion Matrix:")
    print(confusion_matrix(y_test, y_pred))

    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, digits=4))

    print("ROC-AUC:", roc_auc_score(y_test, y_proba))
    print("PR-AUC:", average_precision_score(y_test, y_proba))


def save_model(model):
    model_path = MODEL_DIR / "random_forest_model.joblib"
    joblib.dump(model, model_path)
    print(f"\nModel saved to: {model_path}")

def show_feature_importance(model, X_train):
    importance = pd.DataFrame({
        "feature": X_train.columns,
        "importance": model.feature_importances_,
    }).sort_values("importance", ascending=False)

    print("\nTop 15 Important Features:")
    print(importance.head(15))


def main():
    X_train, X_test, y_train, y_test = load_data()

    print("Training rows:", X_train.shape[0])
    print("Testing rows:", X_test.shape[0])
    print("Number of features:", X_train.shape[1])

    model = train_model(X_train, y_train)
    evaluate_model(model, X_test, y_test)
    show_feature_importance(model, X_train)
    save_model(model)


if __name__ == "__main__":
    main()
