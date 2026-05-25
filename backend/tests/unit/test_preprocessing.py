import pandas as pd

from ml.preprocessing import (
    split_chronologically,
    encode_high_cardinality_post_split,
    drop_raw_and_identifier_columns,
)


def test_split_chronologically():
    df = pd.DataFrame({
        "timestamp": pd.to_datetime([
            "2025-01-01",
            "2025-01-02",
            "2025-01-03",
            "2025-01-04",
            "2025-01-05",
        ]),
        "value": [1, 2, 3, 4, 5]
    })

    train, test = split_chronologically(df, test_frac=0.4)

    assert train["timestamp"].max() < test["timestamp"].min()


def test_high_cardinality_encoding():
    X_train = pd.DataFrame({
        "merchant_id": ["A", "A", "B", "C"]
    })

    X_test = pd.DataFrame({
        "merchant_id": ["A", "D"]
    })

    y_train = pd.Series([1, 0, 1, 0])

    X_train_enc, X_test_enc, maps = encode_high_cardinality_post_split(
        X_train,
        X_test,
        y_train,
        ["merchant_id"]
    )

    assert "merchant_id_fraud_rate" in X_train_enc.columns
    assert "merchant_id" not in X_train_enc.columns

    global_rate = y_train.mean()

    assert (
        X_test_enc["merchant_id_fraud_rate"].iloc[1]
        == global_rate
    )


def test_drop_raw_and_identifier_columns():
    df = pd.DataFrame({
        "transaction_id": [1],
        "card_id": ["A"],
        "timestamp": ["2025-01-01"],
        "feature_x": [123]
    })

    result = drop_raw_and_identifier_columns(df)

    assert "transaction_id" not in result.columns
    assert "card_id" not in result.columns
    assert "feature_x" in result.columns