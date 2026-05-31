"""
seed_demo_transactions.py
=========================
Build the committed static artifact backend/ml/data/demo/demo_transactions.json
used by GET /api/v1/demo/transactions and the frontend "Model Demo" page.

Provenance (matches version2 training pipeline):
- Source: backend/ml/data/raw/transactions.csv (the raw CSV that
  ml/preprocessing.run() loads as DATA_PATH).
- Split: ml.preprocessing.split_chronologically with the same default
  test_frac=0.20 used by version2 — split_ts = timestamp.quantile(0.80,
  nearest); test set = rows with timestamp > split_ts. These are the same
  rows that become X_test2/y_test2 after feature engineering, so the model
  has never seen them.
- Sampling: stratified by is_fraud (half fraud / half legit when possible),
  deterministic via a fixed RNG seed. Re-running this script produces the
  same artifact.

The artifact is shape-stable: each record holds the ingest payload fields
PLUS is_fraud in a SEPARATE field. is_fraud is ground truth for
display/comparison only and must never be POSTed to /api/v1/transactions.

Run:
    cd backend
    python -m scripts.seed_demo_transactions
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ml.preprocessing import DATA_PATH, load_raw_transactions, split_chronologically


BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BASE_DIR / "ml" / "data" / "demo"
OUTPUT_PATH = OUTPUT_DIR / "demo_transactions.json"

# Stratified sample: ~20 rows total, half fraud / half legit when available.
SAMPLE_SEED = 42
N_FRAUD = 10
N_LEGIT = 10

# Fields the POST /api/v1/transactions body accepts. Order kept stable for
# readable diffs in the committed JSON.
INGEST_FIELDS: list[str] = [
    "card_id",
    "merchant_id",
    "timestamp",
    "enriched_amount_usd",
    "issuing_bank_country",
    "transaction_country",
    "cvv2_result",
    "avs_result",
    "pan_entry_mode",
    "authentication",
    "card_type",
    "channel",
    "transaction_type",
    "merchant_category_code",
    # optional persistence-only
    "transaction_amount",
    "transaction_currency",
    "transaction_city",
    "terminal_id",
]


def _to_record(row: pd.Series) -> dict:
    """Convert one raw CSV row into a demo record dict.

    Keeps ingest fields under their normal names, plus:
      * transaction_id : the raw-CSV id (display only — a new DB id is minted
        when the row is POSTed).
      * is_fraud : ground-truth label (0/1), display only.
    """
    record: dict = {"transaction_id": row["transaction_id"]}

    for field in INGEST_FIELDS:
        value = row.get(field)
        if pd.isna(value):
            record[field] = None
            continue
        if field == "timestamp":
            # ISO-8601 string; FastAPI parses this into datetime.
            record[field] = pd.Timestamp(value).isoformat()
        elif field in {"enriched_amount_usd", "transaction_amount"}:
            record[field] = float(value)
        elif field == "merchant_category_code":
            # raw CSV stores MCCs as int; ingest expects str.
            record[field] = str(int(value))
        else:
            record[field] = value if not isinstance(value, (pd.Timestamp,)) else value.isoformat()

    record["is_fraud"] = int(row["is_fraud"])
    return record


def build_demo_records() -> list[dict]:
    df = load_raw_transactions(DATA_PATH)
    _train, test_df = split_chronologically(df)  # default test_frac=0.20

    fraud_pool = test_df[test_df["is_fraud"] == 1]
    legit_pool = test_df[test_df["is_fraud"] == 0]

    n_fraud = min(N_FRAUD, len(fraud_pool))
    n_legit = min(N_LEGIT, len(legit_pool))

    fraud_sample = fraud_pool.sample(n=n_fraud, random_state=SAMPLE_SEED)
    legit_sample = legit_pool.sample(n=n_legit, random_state=SAMPLE_SEED)

    combined = pd.concat([fraud_sample, legit_sample]).sort_values("timestamp")

    print(
        f"Test split rows: {len(test_df):,} "
        f"(fraud={len(fraud_pool):,}, legit={len(legit_pool):,}). "
        f"Sampled {n_fraud} fraud + {n_legit} legit = {len(combined)} demo rows."
    )

    return [_to_record(row) for _, row in combined.iterrows()]


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    records = build_demo_records()
    OUTPUT_PATH.write_text(json.dumps(records, indent=2))
    print(f"Wrote {len(records)} records -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
