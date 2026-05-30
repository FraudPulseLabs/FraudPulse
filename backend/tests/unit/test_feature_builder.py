"""
Scratch script to manually exercise RealtimeFeatureBuilder.
Run from the backend/ directory:
    python -m tests.unit.test_feature_builder

Checks:
    1. Builder loads artefacts without error
    2. Feature dict contains all 32 expected keys
    3. Vector shape is (1, 32)
    4. No features defaulted to 0 due to missing keys (watch the WARNING logs)
    5. Known edge cases: cold-start card, unknown MCC, cross-border flag
"""

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

# Make sure backend/ is on the path when running as a plain script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.services.realtime_feature_builder import RealtimeFeatureBuilder

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)-8s %(name)s — %(message)s",
)

builder = RealtimeFeatureBuilder()
print(f"\nBuilder ready — expects {builder.feature_count} features")
print("Feature order:", builder.feature_order)


# =============================================================================
# HELPERS
# =============================================================================

def run_case(label: str, transaction: dict, card_history: dict):
    print(f"\n{'='*60}")
    print(f"CASE: {label}")
    print(f"{'='*60}")
    features, vector = builder.build(transaction, card_history)

    print(f"\n--- Features ({len(features)}) ---")
    for k, v in sorted(features.items()):
        print(f"  {k:<45} {v}")

    print(f"\n--- Vector ---")
    print(f"  shape : {vector.shape}")
    print(f"  dtype : {vector.dtype}")
    print(f"  values: {np.round(vector[0], 4)}")

    # Sanity checks
    assert vector.shape == (1, builder.feature_count), (
        f"Shape mismatch: got {vector.shape}, expected (1, {builder.feature_count})"
    )
    assert vector.dtype == np.float32, "dtype should be float32"
    assert not np.any(np.isnan(vector)), "NaN in vector — check feature computation"
    assert not np.any(np.isinf(vector)), "Inf in vector — check amount_zscore on cold start"

    print("\n  ✓ shape, dtype, nan, inf checks passed")
    return features, vector


# =============================================================================
# CASE 1 — Normal returning cardholder, domestic, known MCC
# =============================================================================
run_case(
    label="Normal domestic transaction — returning cardholder",
    transaction={
        "timestamp":             datetime(2024, 6, 15, 14, 30, tzinfo=timezone.utc),
        "enriched_amount_usd":   85.00,
        "issuing_bank_country":  "US",
        "transaction_country":   "US",
        "cvv2_result":           "MATCH",
        "avs_result":            "FULL_MATCH",
        "pan_entry_mode":        "CHIP",
        "authentication":        "PIN",
        "card_type":             "Debit",
        "channel":               "POS",
        "transaction_type":      "purchase",
        "merchant_category_code": "5411",
    },
    card_history={
        "txn_count":          42,
        "mean_amt":           78.50,
        "std_amt":            22.10,
        "last_ts":            1718450000.0,
        "current_ts":         1718453600.0,   # 1 hour later
        "recent_timestamps":  [1718450000.0, 1718449000.0],
    },
)


# =============================================================================
# CASE 2 — Cold-start card (first transaction ever)
# feature_engineering.py should return cold-start defaults, not NaN/Inf
# =============================================================================
run_case(
    label="Cold-start card — first transaction",
    transaction={
        "timestamp":             datetime(2024, 6, 15, 2, 15, tzinfo=timezone.utc),  # night
        "enriched_amount_usd":   1200.00,
        "issuing_bank_country":  "US",
        "transaction_country":   "US",
        "cvv2_result":           "MATCH",
        "avs_result":            "FULL_MATCH",
        "pan_entry_mode":        "ONLINE",
        "authentication":        "CVV2",
        "card_type":             "Credit",
        "channel":               "ECOMMERCE",
        "transaction_type":      "purchase",
        "merchant_category_code": "5999",
    },
    card_history={
        "txn_count":          0,
        "mean_amt":           0.0,
        "std_amt":            0.0,
        "last_ts":            None,
        "current_ts":         1718410500.0,
        "recent_timestamps":  [],
    },
)


# =============================================================================
# CASE 3 — Cross-border, velocity burst, unknown MCC (falls back to global rate)
# =============================================================================
run_case(
    label="Cross-border + velocity burst + unknown MCC",
    transaction={
        "timestamp":             datetime(2024, 6, 15, 22, 45, tzinfo=timezone.utc),
        "enriched_amount_usd":   430.00,
        "issuing_bank_country":  "US",
        "transaction_country":   "NG",          # cross-border
        "cvv2_result":           "NOT_PROVIDED",
        "avs_result":            "NOT_PERFORMED",
        "pan_entry_mode":        "MAGSTRIPE",
        "authentication":        "NONE",
        "card_type":             "Credit",
        "channel":               "ATM",
        "transaction_type":      "withdrawal",
        "merchant_category_code": "9999",        # not in encoding map → global_rate
    },
    card_history={
        "txn_count":          8,
        "mean_amt":           60.00,
        "std_amt":            15.00,
        "last_ts":            1718495800.0,
        "current_ts":         1718495900.0,      # 100 seconds after last
        "recent_timestamps":  [                  # 6 txns in the last hour
            1718493000.0,
            1718493500.0,
            1718494000.0,
            1718494800.0,
            1718495200.0,
            1718495800.0,
        ],
    },
)


# =============================================================================
# CASE 4 — Verify merchant_category_code fallback explicitly
# =============================================================================
print(f"\n{'='*60}")
print("CASE: MCC encoding — known vs unknown vs missing")
print(f"{'='*60}")

known_mcc   = builder._encode_mcc("5411")   # in the map
unknown_mcc = builder._encode_mcc("0000")   # not in map → global_rate
empty_mcc   = builder._encode_mcc("")       # blank → global_rate

enc         = builder._encoding_maps["merchant_category_code"]
global_rate = enc["global_rate"]

print(f"  known MCC  5411 → {known_mcc}  (expected {enc['map']['5411']})")
print(f"  unknown    0000 → {unknown_mcc}  (expected global_rate={global_rate})")
print(f"  empty           → {empty_mcc}  (expected global_rate={global_rate})")

assert known_mcc   == enc["map"]["5411"]
assert unknown_mcc == global_rate
assert empty_mcc   == global_rate
print("  ✓ MCC encoding checks passed")


print("\n\nAll cases completed.")