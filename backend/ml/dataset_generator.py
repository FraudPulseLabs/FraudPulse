import pandas as pd
import numpy as np
import random
import uuid
from datetime import datetime, timedelta

# If you have src.config, swap this back:
# from src.config import DATA_DIR
from pathlib import Path
DATA_DIR = Path("ml/data")

# =============================================================================
# CONFIG
# =============================================================================
SEED = 42
np.random.seed(SEED)
random.seed(SEED)

N_TRANSACTIONS = random.randint(60000, 90000)
START_DATE     = datetime(2025, 1, 1)
TARGET_FRAUD   = int(N_TRANSACTIONS * random.uniform(0.03, 0.05))

# =============================================================================
# STATIC DATA
# =============================================================================
COUNTRY_CITY_MAP = {
    "USA": ["New York", "Los Angeles", "Chicago"],
    "GBR": ["London", "Manchester"],
    "KEN": ["Nairobi", "Mombasa"],
    "SGP": ["Singapore", "Singapore"],
    "ARE": ["Dubai", "Abu Dhabi"],
    "IND": ["Mumbai", "Delhi"],
}

CURRENCIES = {
    "USA": "USD", "GBR": "GBP", "KEN": "KES",
    "SGP": "SGD", "ARE": "AED", "IND": "INR",
}

FX_TO_USD = {
    "USD": 1.0000, "GBP": 1.2700, "KES": 0.0077,
    "SGD": 0.7400, "AED": 0.2720, "INR": 0.0120,
}

_HIGH_RISK_MCC = {"7995", "4829", "6012", "5933", "5542"}
_LOW_RISK_MCC  = {"5411", "5812", "5732", "5999", "5311", "5541", "5651", "5814"}
ALL_MCC        = sorted(_HIGH_RISK_MCC | _LOW_RISK_MCC)

MCC_FRAUD_WEIGHT = {
    "7995": 5.0, "4829": 4.5, "6012": 4.0, "5933": 3.5, "5542": 3.0,
    "5732": 2.5, "5651": 2.0, "5814": 1.2, "5812": 1.0, "5411": 1.0,
    "5541": 1.0, "5311": 1.0, "5999": 1.0,
}

PAN_ENTRY_FRAUD_WEIGHT = {
    "MAGSTRIPE": 6.0, "CONTACTLESS": 2.5, "CHIP": 0.3,
}

CARD_TYPE_FRAUD_WEIGHT = {
    "Prepaid": 3.5, "Credit": 1.5, "Debit": 1.0,
}

# Cold-start spend profile — lognormal(mu, sigma) in USD.
# FIX: mu values raised so cold-start draws produce realistic USD amounts.
# Previous values (Prepaid 3.0, Debit 3.5, Credit 4.0) were calibrated to
# native currency magnitudes. After the amount_hist FX fix, cold-start now
# also needs to anchor in USD: e^4.0=$55, e^4.5=$90, e^5.0=$148.
CARD_TYPE_SPEND_PROFILE = {
    "Prepaid": (3.5, 0.8),   # median ~$33 — low-spend anonymous card
    "Debit":   (4.2, 0.9),   # median ~$67 — everyday spend
    "Credit":  (4.8, 1.0),   # median ~$121 — higher spend, wider range
}

AVS_COUNTRIES = {"USA", "GBR"}
CHANNELS      = ["ECOMMERCE", "POS", "ATM"]
CARD_TYPES    = ["Debit", "Credit", "Prepaid"]

# =============================================================================
# HELPERS
# =============================================================================
def generate_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"

def get_distance_tier(c1: str, c2: str) -> str:
    return "SAME" if c1 == c2 else "CROSS_BORDER"

def sample_amount_lognormal(amount_hist: list, card_type: str = "Debit") -> float:
    if len(amount_hist) < 5:
        mu, sigma = CARD_TYPE_SPEND_PROFILE.get(card_type, (3.5, 0.8))
        return round(float(np.random.lognormal(mean=mu, sigma=sigma)), 2)
    log_vals = np.log(np.maximum(amount_hist, 1))
    mu  = float(np.mean(log_vals))
    sig = float(max(0.3, np.std(log_vals)))
    return round(float(np.random.lognormal(mean=mu, sigma=sig)), 2)

def _clamp(val: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, val))

# =============================================================================
# LAYER 1 — RISK ENGINE  (hidden, never written to output)
# =============================================================================
_W_MCC        = 0.25
_W_CHANNEL    = 0.15
_W_GEOGRAPHY  = 0.25
_W_VELOCITY   = 0.20
_W_ENTRY_MODE = 0.15

def _mcc_risk_score(mcc: str) -> float:
    if mcc in _HIGH_RISK_MCC: return 0.8
    if mcc in _LOW_RISK_MCC:  return 0.1
    return 0.4

def _channel_risk_score(channel: str) -> float:
    return {"ECOMMERCE": 0.7, "POS": 0.25, "ATM": 0.25}.get(channel, 0.35)

def _entry_mode_risk_score(pan_entry_mode: str) -> float:
    return {"MAGSTRIPE": 0.85, "CONTACTLESS": 0.45, "CHIP": 0.05, "ONLINE": 0.55}.get(pan_entry_mode, 0.4)

def _geography_risk_score(home_country: str, txn_country: str) -> float:
    return {"SAME": 0.05, "CROSS_BORDER": 0.85}[get_distance_tier(home_country, txn_country)]

def _velocity_risk_score(gap_seconds: float) -> float:
    minutes = gap_seconds / 60.0
    return _clamp(1.0 / (1.0 + np.exp(0.15 * (minutes - 10))))

def compute_risk_score(mcc, channel, pan_entry_mode, home_country, txn_country,
                       gap_seconds, watchlist_merchant=False) -> float:
    score = (
        _W_MCC        * _mcc_risk_score(mcc)
        + _W_CHANNEL    * _channel_risk_score(channel)
        + _W_ENTRY_MODE * _entry_mode_risk_score(pan_entry_mode)
        + _W_GEOGRAPHY  * _geography_risk_score(home_country, txn_country)
        + _W_VELOCITY   * _velocity_risk_score(gap_seconds)
    )
    if watchlist_merchant:
        score += 0.15
    return _clamp(score)

# =============================================================================
# LAYER 2 — ENTITY GENERATION
# =============================================================================
def generate_merchants(n: int = 700) -> pd.DataFrame:
    rows = []
    for _ in range(n):
        country = random.choice(list(COUNTRY_CITY_MAP.keys()))
        mcc     = random.choice(ALL_MCC)
        channel = random.choices(CHANNELS, weights=[0.5, 0.4, 0.1])[0]
        internal_watchlist = random.random() < 0.08

        if channel == "ATM":
            entry_mode_profile = random.choices(
                ["CHIP", "MAGSTRIPE", "CONTACTLESS"], weights=[0.80, 0.12, 0.08])[0]
        elif channel == "POS":
            entry_mode_profile = random.choices(
                ["CHIP", "CONTACTLESS", "MAGSTRIPE"], weights=[0.55, 0.40, 0.05])[0]
        else:
            entry_mode_profile = "ONLINE"

        rows.append({
            "merchant_id":         generate_id("m"),
            "country":             country,
            "mcc":                 mcc,
            "channel":             channel,
            "_internal_watchlist": internal_watchlist,
            "_entry_mode_profile": entry_mode_profile,
        })

    df = pd.DataFrame(rows)
    ranks         = np.arange(1, len(df) + 1, dtype=float)
    weights       = 1.0 / np.power(ranks, 1.1)
    df["_weight"] = weights / weights.sum()
    return df


def sample_merchant(merchants_df: pd.DataFrame, weights: np.ndarray):
    return merchants_df.iloc[np.random.choice(len(merchants_df), p=weights)]


def generate_cards(n_cards: int = 3000) -> pd.DataFrame:
    rows = []
    for _ in range(n_cards):
        country = random.choice(list(COUNTRY_CITY_MAP.keys()))
        is_watchlist = random.random() < 0.05
        card_type = random.choice(CARD_TYPES)
        rows.append({
            "card_id":                 generate_id("c"),
            "card_type":               card_type,
            "home_country":            country,
            "_internal_watchlist":     is_watchlist,
            "_card_type_fraud_weight": CARD_TYPE_FRAUD_WEIGHT[card_type],
        })
    return pd.DataFrame(rows)

# =============================================================================
# FRAUD SLOT PRE-ASSIGNMENT
# =============================================================================
def assign_fraud_slots(card_ids, target_fraud, seed=SEED, card_type_weights=None):
    rng           = np.random.default_rng(seed)
    n_compromised = max(1, int(len(card_ids) * 0.12))
    compromised   = set(rng.choice(card_ids, size=n_compromised, replace=False))

    burst_caps = {
        cid: int(rng.integers(2, 7)) if cid in compromised
             else int(rng.integers(0, 3))
        for cid in card_ids
    }

    effective_caps = {
        cid: burst_caps[cid] * (card_type_weights.get(cid, 1.0) if card_type_weights else 1.0)
        for cid in card_ids
    }
    total_capacity = sum(effective_caps.values())

    alloc = {
        cid: min(burst_caps[cid],
                 max(0, round(effective_caps[cid] / total_capacity * target_fraud)))
        for cid in card_ids
    }

    diff     = target_fraud - sum(alloc.values())
    eligible = [cid for cid in card_ids if alloc[cid] < burst_caps[cid]]
    rng.shuffle(eligible)
    for cid in eligible:
        if diff == 0: break
        if diff > 0:   alloc[cid] += 1; diff -= 1
        elif alloc[cid] > 0: alloc[cid] -= 1; diff += 1

    return alloc

# =============================================================================
# LAYER 3 — TRANSACTION GENERATION
# =============================================================================
OUTPUT_COLUMNS = [
    "transaction_id", "timestamp",
    "card_id", "card_type", "issuing_bank_country",
    "merchant_id", "merchant_category_code",
    "channel", "transaction_type",
    "transaction_country", "transaction_city",
    "transaction_currency", "transaction_amount", "enriched_amount_usd",
    "card_present", "cardholder_present", "pan_entry_mode",
    "terminal_id", "authentication",
    "cvv2_result", "avs_result",
    "is_fraud",
]


def build_txn(card, merchant, ts, amount, txn_country, channel, txn_type,
              pan_entry_mode, card_present, cardholder_present,
              auth, cvv2_result, avs_result, is_fraud) -> dict:
    return {
        "transaction_id":         generate_id("t"),
        "timestamp":              ts.isoformat(),
        "card_id":                card["card_id"],
        "card_type":              card["card_type"],
        "issuing_bank_country":   card["home_country"],
        "merchant_id":            merchant["merchant_id"],
        "merchant_category_code": merchant["mcc"],
        "channel":                channel,
        "transaction_type":       txn_type,
        "transaction_country":    txn_country,
        "transaction_city":       random.choice(COUNTRY_CITY_MAP[txn_country]),
        "transaction_currency":   CURRENCIES.get(txn_country, "USD"),
        "transaction_amount":     round(amount, 2),
        "enriched_amount_usd":    round(amount * FX_TO_USD.get(CURRENCIES.get(txn_country, "USD"), 1.0), 2),
        "card_present":           card_present,
        "cardholder_present":     cardholder_present,
        "pan_entry_mode":         pan_entry_mode,
        "terminal_id":            generate_id("term"),
        "authentication":         auth,
        "cvv2_result":            cvv2_result,
        "avs_result":             avs_result,
        "is_fraud":               is_fraud,
    }


# =============================================================================
# NORMAL TRANSACTION
# =============================================================================
def generate_normal_txn(card, merchant, prev_ts: datetime, amount_hist: list) -> dict:
    # --- VELOCITY ---
    # FIX: was 5–180 min. Now 1–180 min with a long tail, creating
    # sub-5-minute legitimate transactions that overlap with fraud velocity.
    gap_seconds = int(np.random.exponential(scale=45 * 60))          # mean ~45 min
    gap_seconds = max(60, min(gap_seconds, 8 * 3600))                 # clamp 1 min–8 hr

    ts = prev_ts + timedelta(seconds=gap_seconds)

    # --- GEOGRAPHY ---
    # FIX: was 80–95% domestic, fully randomised upper bound.
    # Now a fixed 85% domestic rate — gives a consistent but not extreme lean.
    # Also: 5% chance of a truly random foreign country (travel noise).
    r = random.random()
    if r < 0.85:
        txn_country = card["home_country"]
    elif r < 0.90:
        txn_country = merchant["country"]   # merchant's country (plausible travel)
    else:
        txn_country = random.choice(list(COUNTRY_CITY_MAP.keys()))   # fully random

    # --- AMOUNT ---
    # amount_hist now stores enriched_amount_usd (USD), so lognormal draws
    # are anchored in USD throughout the card's lifetime.
    # Floor raised from $1.00 to $2.00 — sub-dollar legit transactions are
    # implausible outside micro-tipping contexts not present in this dataset.
    # Big-ticket rate raised from 8% to 15% — more overlap with fraud range.
    amount = max(2.0, sample_amount_lognormal(amount_hist, card["card_type"]))
    if random.random() < 0.15:   # big-ticket: elevated spend overlaps fraud range
        amount = round(amount * random.uniform(1.5, 4.0), 2)

    channel  = merchant["channel"]
    txn_type = "withdrawal" if channel == "ATM" else "purchase"

    pan_entry_mode = merchant["_entry_mode_profile"]

    if channel == "ATM":
        card_present, cardholder_present = 1, 1
    elif channel == "POS":
        card_present = 1
        cardholder_present = 0 if random.random() < 0.08 else 1
    else:
        card_present = 0
        # 30% absent: card-on-file, MIT, subscriptions, delivery charges —
        # cardholder is not actively present for a large share of e-commerce.
        cardholder_present = 0 if random.random() < 0.30 else 1

    # --- AUTH ---
    # FIX: was 8% NONE across the board.
    # Now 15% NONE — more realistic fallback rate, more overlap with fraud.
    if channel == "ATM":
        auth = random.choices(["PIN", "NONE"], weights=[0.87, 0.13])[0]
    elif channel == "POS":
        auth = random.choices(
            ["PIN", "CVV2", "BIOMETRICS", "NONE"], weights=[0.62, 0.14, 0.10, 0.14])[0]
    else:
        auth = random.choices(
            ["OTP", "BIOMETRICS", "CVV2", "NONE"], weights=[0.45, 0.28, 0.12, 0.15])[0]

    # CVV2
    if channel == "ECOMMERCE":
        cvv2_result = "NOT_PROVIDED" if cardholder_present == 0 else "MATCH"
    else:
        cvv2_result = "NOT_APPLICABLE"

    # --- AVS ---
    # FIX: was 82% FULL_MATCH for legitimate ecomm — now introduce PARTIAL_MATCH
    # at higher rate (30%) to reduce the clean signal gap with fraud.
    if channel != "ECOMMERCE" or txn_country not in AVS_COUNTRIES:
        avs_result = "NOT_PERFORMED"
    elif cardholder_present == 0:
        avs_result = "NOT_PERFORMED"
    else:
        avs_result = random.choices(
            ["FULL_MATCH", "PARTIAL_MATCH"],
            weights=[0.70, 0.30]
        )[0]

    return build_txn(card, merchant, ts, amount, txn_country, channel, txn_type,
                     pan_entry_mode, card_present, cardholder_present,
                     auth, cvv2_result, avs_result, is_fraud=0)


# =============================================================================
# FRAUD TRANSACTION
# =============================================================================
def generate_fraud_txn(card, merchant, prev_ts: datetime, amount_hist: list) -> dict:
    # --- VELOCITY ---
    # FIX: was 5–120 s (no overlap with normal).
    # Now a mix: 60% rapid burst (30–300 s), 40% delayed (5–60 min).
    # Delayed fraud = account takeover sessions, not pure card cloning.
    if random.random() < 0.60:
        gap_seconds = random.randint(30, 300)        # rapid burst
    else:
        gap_seconds = random.randint(5 * 60, 60 * 60)  # delayed — overlaps normal

    ts = prev_ts + timedelta(seconds=gap_seconds)

    # --- GEOGRAPHY ---
    # FIX: was always fully random country.
    # Now 35% of fraud is domestic (stolen cards used locally, account takeover
    # from same country). Still elevated vs legit 15% foreign rate, but not extreme.
    if random.random() < 0.35:
        txn_country = card["home_country"]
    else:
        txn_country = random.choice(list(COUNTRY_CITY_MAP.keys()))

    # --- AMOUNT ---
    # FIX: was 3–8x baseline or $200–$1200, with no overlap.
    # Now: 25% of fraud uses amounts indistinguishable from normal spend
    # (small-test transactions to verify cards before larger hits).
    baseline = (
        float(np.exp(np.mean(np.log(np.maximum(amount_hist, 1)))))
        if len(amount_hist) >= 3 else 50.0
    )
    r = random.random()
    if r < 0.30:
        # Card-test / probe: fully overlaps legitimate spend.
        # Raised from 25% to 30% — more low-amount fraud reduces median separation.
        amount = round(max(2.0, sample_amount_lognormal(amount_hist, card["card_type"])), 2)
    elif r < 0.70:
        # Classic fraud spike — kept but hard floor lowered from $150 to $80
        # so the distribution tail starts closer to the legit 75th pct ($45-$120).
        amount = round(max(baseline * random.uniform(1.8, 5.0),
                           float(np.random.uniform(80, 700))), 2)
    else:
        # Moderate fraud — 1–2x baseline, overlaps legit big-ticket spend.
        # Hard floor lowered from $50 to $20 for tighter overlap.
        amount = round(max(baseline * random.uniform(1.0, 2.0),
                           float(np.random.uniform(20, 300))), 2)

    channel = random.choices(["ECOMMERCE", "POS", "ATM"], weights=[0.6, 0.3, 0.1])[0]

    # --- PAN ENTRY MODE ---
    # FIX: was heavily biased to MAGSTRIPE/CONTACTLESS.
    # Now CHIP is more represented (stolen physical cards with PIN compromise
    # is a real and growing vector). Still higher-risk modes predominate.
    if channel == "ATM":
        txn_type, card_present = "withdrawal", 1
        pan_entry_mode = random.choices(
            ["MAGSTRIPE", "CONTACTLESS", "CHIP"],
            weights=[0.50, 0.25, 0.25]   # more chip than before
        )[0]
        if pan_entry_mode == "CHIP":
            cardholder_present = 0 if random.random() < 0.45 else 1
            auth = random.choices(["PIN", "NONE"], weights=[0.55, 0.45])[0]
        elif pan_entry_mode == "CONTACTLESS":
            cardholder_present = 0 if random.random() < 0.70 else 1   # less extreme
            auth = random.choices(["NONE", "PIN"], weights=[0.65, 0.35])[0]
        else:
            cardholder_present = 0 if random.random() < 0.80 else 1   # less extreme
            auth = random.choices(["NONE", "PIN"], weights=[0.65, 0.35])[0]

    elif channel == "POS":
        txn_type, card_present = "purchase", 1
        pan_entry_mode = random.choices(
            ["MAGSTRIPE", "CONTACTLESS", "CHIP"],
            weights=[0.30, 0.40, 0.30]   # more chip (stolen card + PIN)
        )[0]
        if pan_entry_mode == "CHIP":
            cardholder_present = 0 if random.random() < 0.40 else 1   # less extreme
            auth = random.choices(["PIN", "NONE", "CVV2"], weights=[0.40, 0.42, 0.18])[0]
        elif pan_entry_mode == "CONTACTLESS":
            cardholder_present = 0 if random.random() < 0.65 else 1   # less extreme
            auth = random.choices(["NONE", "PIN"], weights=[0.60, 0.40])[0]
        else:
            cardholder_present = 0 if random.random() < 0.75 else 1
            auth = random.choices(["NONE", "PIN", "CVV2"], weights=[0.55, 0.28, 0.17])[0]

    else:  # ECOMMERCE
        txn_type, card_present = "purchase", 0
        pan_entry_mode = "ONLINE"
        # TARGET correlation ~-0.15 between cardholder_present and is_fraud.
        # Fraud ECOMMERCE: 55% absent (down from 80%).
        #   Rationale: ATO with full login session = present; pure CNP with
        #   stolen card number only = absent. Both are common fraud vectors.
        # Normal ECOMMERCE: 30% absent (up from 15%).
        #   Rationale: card-on-file/MIT/subscription charges are very common
        #   and grow as a share of e-commerce — cardholder is not actively
        #   present for recurring billing, delivery charges, etc.
        cardholder_present = 0 if random.random() < 0.55 else 1
        # Auth for fraud ECOMMERCE: further reduced NONE to 38%.
        # ATO sessions (cardholder_present=1) will tend to have OTP/CVV2
        # since fraudster has login access. Pure CNP is NONE-heavy.
        auth = random.choices(
            ["NONE", "CVV2", "OTP", "BIOMETRICS"],
            weights=[0.38, 0.34, 0.20, 0.08]
        )[0]

    # --- CVV2 ---
    # FIX: was 80% NOT_PROVIDED. Now 35% have a MATCH (card data stolen with CVV2).
    if channel == "ECOMMERCE":
        cvv2_result = random.choices(
            ["MATCH", "NOT_PROVIDED"],
            weights=[0.35, 0.65]   # more fraudsters have full card details
        )[0]
    else:
        cvv2_result = "NOT_APPLICABLE"

    # --- AVS ---
    # FIX: was 45% FULL_MATCH is too low for fraud — makes it nearly deterministic
    # when combined with other fields. Now 25% FULL_MATCH (fraudsters with
    # full identity packages) to reduce that clean split.
    if channel != "ECOMMERCE" or txn_country not in AVS_COUNTRIES:
        avs_result = "NOT_PERFORMED"
    else:
        avs_result = random.choices(
            ["FULL_MATCH", "PARTIAL_MATCH", "NOT_PERFORMED"],
            weights=[0.20, 0.40, 0.40]
        )[0]

    return build_txn(card, merchant, ts, amount, txn_country, channel, txn_type,
                     pan_entry_mode, card_present, cardholder_present,
                     auth, cvv2_result, avs_result, is_fraud=1)


# =============================================================================
# MAIN
# =============================================================================
def generate_dataset():
    merchants = generate_merchants()
    cards     = generate_cards()

    merchant_weights = merchants["_weight"].values.copy()

    mcc_bias   = merchants["mcc"].map(MCC_FRAUD_WEIGHT).fillna(1.0).values
    entry_bias = merchants["_entry_mode_profile"].map(PAN_ENTRY_FRAUD_WEIGHT).fillna(1.0).values
    raw_fraud_weights = merchant_weights * mcc_bias * entry_bias
    merchant_fraud_weights = raw_fraud_weights / raw_fraud_weights.sum()

    card_ids = list(cards["card_id"])
    n_cards  = len(cards)

    raw_counts = np.array([random.randint(10, 40) for _ in range(n_cards)], dtype=float)
    scaled     = raw_counts / raw_counts.sum() * N_TRANSACTIONS
    txn_counts = np.floor(scaled).astype(int)
    remainder  = N_TRANSACTIONS - txn_counts.sum()
    if remainder > 0:
        txn_counts[np.argsort(scaled - txn_counts)[::-1][:remainder]] += 1
    txn_counts = np.maximum(txn_counts, 1)

    card_type_bias    = cards["card_type"].map(CARD_TYPE_FRAUD_WEIGHT).fillna(1.0).values
    card_type_weights = dict(zip(card_ids, card_type_bias))
    fraud_alloc       = assign_fraud_slots(card_ids, TARGET_FRAUD,
                                           card_type_weights=card_type_weights)

    txns = []
    for idx, (_, card) in enumerate(cards.iterrows()):
        cid   = card["card_id"]
        n_txn = int(txn_counts[idx])

        n_fraud         = min(fraud_alloc.get(cid, 0), n_txn)
        fraud_positions = set(random.sample(range(n_txn), n_fraud)) if n_fraud > 0 else set()

        prev_ts     = START_DATE + timedelta(days=random.randint(0, 30))
        amount_hist: list = []

        for i in range(n_txn):
            is_fraud_txn = i in fraud_positions
            merchant = sample_merchant(
                merchants,
                merchant_fraud_weights if is_fraud_txn else merchant_weights
            )
            txn = (
                generate_fraud_txn(card, merchant, prev_ts, amount_hist)
                if is_fraud_txn else
                generate_normal_txn(card, merchant, prev_ts, amount_hist)
            )
            # FIX: store enriched_amount_usd (USD) not native transaction_amount.
            # Native amounts anchor lognormal draws on KES/INR magnitudes
            # (e.g. 500 KES stored as 500), producing sub-dollar USD values
            # after FX conversion. Fraud used hard USD floors ($150-$900),
            # creating a near-clean split. USD history fixes the anchor.
            amount_hist.append(txn["enriched_amount_usd"])
            if len(amount_hist) > 20:
                amount_hist = amount_hist[-20:]
            prev_ts = datetime.fromisoformat(txn["timestamp"])
            txns.append(txn)

    df = pd.DataFrame(txns)
    assert len(df) == N_TRANSACTIONS, f"Row count mismatch: {len(df)} != {N_TRANSACTIONS}"

    df = df[OUTPUT_COLUMNS].sort_values("timestamp").reset_index(drop=True)

    actual_fraud = int(df["is_fraud"].sum())
    print("\n--- DATASET SUMMARY ---")
    print(f"Total transactions : {len(df)}")
    print(f"Fraud count        : {actual_fraud}  (target {TARGET_FRAUD})")
    print(f"Fraud %            : {round(df['is_fraud'].mean() * 100, 2)}%  "
          f"(target {round(TARGET_FRAUD / N_TRANSACTIONS * 100, 2)}%)")
    print(f"\nOutput columns ({len(OUTPUT_COLUMNS)}):")
    for col in OUTPUT_COLUMNS:
        print(f"  {col}")

    raw_dir = DATA_DIR / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    out_path = raw_dir / "transactions.csv"
    df.to_csv(out_path, index=False)
    print(f"\nSaved to {out_path}")
    return df


if __name__ == "__main__":
    generate_dataset()