import pandas as pd
import numpy as np
import random
import uuid
from datetime import datetime, timedelta
from src.config import DATA_DIR

# =============================================================================
# CONFIG
# =============================================================================
SEED = 42
np.random.seed(SEED)
random.seed(SEED)

N_TRANSACTIONS = random.randint(30000, 60000)
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

# Fixed FX rates to USD — synthetic only, baked in at generation time.
# Downstream models must use enriched_amount_usd, not transaction_amount,
# to avoid scale artifacts (e.g. 10 000 KES ≈ 77 USD, not 10 000 USD).
FX_TO_USD = {
    "USD": 1.0000,
    "GBP": 1.2700,
    "KES": 0.0077,
    "SGD": 0.7400,
    "AED": 0.2720,
    "INR": 0.0120,
}

# MCC risk classification — internal only, never written to output
_HIGH_RISK_MCC = {"7995", "4829", "6012", "5933", "5542"}
_LOW_RISK_MCC  = {"5411", "5812", "5732", "5999", "5311", "5541", "5651", "5814"}
ALL_MCC        = sorted(_HIGH_RISK_MCC | _LOW_RISK_MCC)

# Per-MCC fraud propensity weight used to bias fraud slot allocation.
# Higher = more likely to appear in fraud transactions.
# Real-world basis: gambling/crypto (7995), money transfer (4829),
# financial services (6012), pawn/secondhand (5933), fuel/unmanned (5542),
# clothing (5651) and electronics (5732) are well-documented fraud vectors.
# Low-risk categories (grocery 5411, restaurant 5812) get baseline weight.
MCC_FRAUD_WEIGHT = {
    "7995": 5.0,   # gambling / crypto — highest fraud propensity
    "4829": 4.5,   # money transfer / wire
    "6012": 4.0,   # financial institution — card testing target
    "5933": 3.5,   # pawn shops / secondhand
    "5542": 3.0,   # fuel / unmanned POS — skimming target
    "5732": 2.5,   # electronics
    "5651": 2.0,   # clothing / apparel
    "5814": 1.2,   # fast food — low but above baseline
    "5812": 1.0,   # restaurants — baseline
    "5411": 1.0,   # grocery — baseline
    "5541": 1.0,   # service stations
    "5311": 1.0,   # department stores
    "5999": 1.0,   # misc retail
}

# PAN entry mode fraud propensity weights — used to bias merchant terminal
# selection for fraud transactions.
# Magstripe = skimming target (no cryptogram, fully clonable).
# Contactless = stolen card tap-and-go above CVM limit.
# Chip = EMV cryptogram verified — implausible to clone at scale.
# ONLINE is ECOMMERCE only; handled separately.
PAN_ENTRY_FRAUD_WEIGHT = {
    "MAGSTRIPE":   6.0,   # skimmed card replay — dominant ATM/POS fraud vector
    "CONTACTLESS": 2.5,   # stolen card, no PIN required below CVM limit
    "CHIP":        0.3,   # valid cryptogram required — near-implausible to clone
}

# Card type fraud propensity — Prepaid highest (weak identity binding),
# Credit moderate, Debit baseline.
CARD_TYPE_FRAUD_WEIGHT = {
    "Prepaid": 3.5,   # anonymous / weak KYC — highest CNP fraud vector
    "Credit":  1.5,   # moderate — dispute/chargeback fraud
    "Debit":   1.0,   # baseline
}

# Cold-start spend profile per card type (log-normal mean, sigma)
CARD_TYPE_SPEND_PROFILE = {
    "Prepaid": (3.0, 0.7),   # low spend, tight range
    "Credit":  (4.0, 0.9),   # higher spend, wider range
    "Debit":   (3.5, 0.8),   # mid spend
}

# Countries with AVS infrastructure — transactions outside these always NOT_PERFORMED
AVS_COUNTRIES = {"USA", "GBR"}

CHANNELS   = ["ECOMMERCE", "POS", "ATM"]
CARD_TYPES = ["Debit", "Credit", "Prepaid"]

# =============================================================================
# HELPERS
# =============================================================================
def generate_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"

def get_distance_tier(c1: str, c2: str) -> str:
    """Two tiers only — SAME (domestic) or CROSS_BORDER (any foreign).
    Country-pair-specific tiers removed to eliminate geographic bias.
    """
    return "SAME" if c1 == c2 else "CROSS_BORDER"

def sample_amount_lognormal(amount_hist: list, card_type: str = "Debit") -> float:
    """Log-normal draw fitted to the card's own transaction history.
    Cold-start (< 5 txns) uses card_type spend profile as prior.
    """
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
_W_ENTRY_MODE = 0.15   # pan_entry_mode risk contribution

def _mcc_risk_score(mcc: str) -> float:
    if mcc in _HIGH_RISK_MCC:
        return 0.8
    if mcc in _LOW_RISK_MCC:
        return 0.1
    return 0.4

def _channel_risk_score(channel: str) -> float:
    return {"ECOMMERCE": 0.7, "POS": 0.25, "ATM": 0.25}.get(channel, 0.35)

def _entry_mode_risk_score(pan_entry_mode: str) -> float:
    """Magstripe = high risk (clonable). Chip = low risk (cryptogram). Online = medium (CNP)."""
    return {
        "MAGSTRIPE":   0.85,
        "CONTACTLESS": 0.45,
        "CHIP":        0.05,
        "ONLINE":      0.55,   # CNP — no physical card verification
    }.get(pan_entry_mode, 0.4)

def _geography_risk_score(home_country: str, txn_country: str) -> float:
    """Risk from card-home vs transaction-country mismatch only.
    Binary: SAME (domestic) or CROSS_BORDER. No country-identity penalties.
    """
    tier_score = {"SAME": 0.05, "CROSS_BORDER": 0.85}
    return tier_score[get_distance_tier(home_country, txn_country)]

def _velocity_risk_score(gap_seconds: float) -> float:
    """Inverse-sigmoid: <60 s → ~0.9, 5 min → ~0.6, 30 min → ~0.2, >1 hr → ~0.05."""
    minutes = gap_seconds / 60.0
    return _clamp(1.0 / (1.0 + np.exp(0.15 * (minutes - 10))))

def compute_risk_score(
    mcc: str,
    channel: str,
    pan_entry_mode: str,
    home_country: str,
    txn_country: str,
    gap_seconds: float,
    watchlist_merchant: bool = False,
) -> float:
    """
    Weighted combination of five risk signals → scalar in [0, 1].
    pan_entry_mode is resolved before this call so it feeds the score.
    Watchlist merchant status bumps the score by 0.15 internally.
    This score is NEVER stored in the dataset.
    """
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

        # Internal watchlist flag — used only by risk engine, not in output
        # Flat rate — decoupled from MCC to prevent double-counting MCC risk
        # in the engine (once via _mcc_risk_score, again via watchlist bump).
        internal_watchlist = random.random() < 0.08

        # Terminal entry mode profile — determines what pan_entry_mode
        # normal transactions at this merchant will use.
        # ATM: mostly chip, some magstripe (legacy machines)
        # POS: mostly chip/contactless, rare magstripe (fallback)
        # ECOMMERCE: always ONLINE
        if channel == "ATM":
            entry_mode_profile = random.choices(
                ["CHIP", "MAGSTRIPE", "CONTACTLESS"],
                weights=[0.80, 0.12, 0.08]
            )[0]
        elif channel == "POS":
            entry_mode_profile = random.choices(
                ["CHIP", "CONTACTLESS", "MAGSTRIPE"],
                weights=[0.55, 0.40, 0.05]
            )[0]
        else:  # ECOMMERCE
            entry_mode_profile = "ONLINE"

        rows.append({
            "merchant_id":            generate_id("m"),
            "country":                country,
            "mcc":                    mcc,
            "channel":                channel,
            "_internal_watchlist":    internal_watchlist,
            "_entry_mode_profile":    entry_mode_profile,
        })

    df = pd.DataFrame(rows)

    # Zipf-like sampling weights — normalised once, fixed forever
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
        # Card-level watchlist: used only by risk engine (upstream hard-block).
        # Watchlisted cards are declined before fraud scoring — never in output.
        is_watchlist = random.random() < 0.05
        card_type = random.choice(CARD_TYPES)
        rows.append({
            "card_id":                  generate_id("c"),
            "card_type":                card_type,
            "home_country":             country,
            "_internal_watchlist":      is_watchlist,
            "_card_type_fraud_weight":  CARD_TYPE_FRAUD_WEIGHT[card_type],
        })
    return pd.DataFrame(rows)

# =============================================================================
# FRAUD SLOT PRE-ASSIGNMENT
# =============================================================================
def assign_fraud_slots(
    card_ids: list,
    target_fraud: int,
    seed: int = SEED,
    card_type_weights: dict = None,
) -> dict:
    """
    Returns { card_id -> n_fraud_txns }, summing to exactly target_fraud.
    Compromised cards (12%) receive 2–6 slots; others receive 0–2.
    card_type_weights: { card_id -> float } propensity multiplier —
    higher-propensity card types (Prepaid) receive proportionally more slots.
    """
    rng           = np.random.default_rng(seed)
    n_compromised = max(1, int(len(card_ids) * 0.12))
    compromised   = set(rng.choice(card_ids, size=n_compromised, replace=False))

    burst_caps = {
        cid: int(rng.integers(2, 7)) if cid in compromised
             else int(rng.integers(0, 3))
        for cid in card_ids
    }

    # Scale burst caps by card type propensity before proportional allocation
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

    # Trim / top-up to hit exactly target_fraud
    diff     = target_fraud - sum(alloc.values())
    eligible = [cid for cid in card_ids if alloc[cid] < burst_caps[cid]]
    rng.shuffle(eligible)
    for cid in eligible:
        if diff == 0:
            break
        if diff > 0:
            alloc[cid] += 1; diff -= 1
        elif alloc[cid] > 0:
            alloc[cid] -= 1; diff += 1

    return alloc

# =============================================================================
# LAYER 3 — TRANSACTION GENERATION  (inference-safe output only)
# =============================================================================
# Columns written to the final CSV — nothing else
OUTPUT_COLUMNS = [
    "transaction_id", "timestamp",
    "card_id", "card_type", "issuing_bank_country",
    "merchant_id", "merchant_category_code",
    "channel", "transaction_type",
    "transaction_country", "transaction_city",
    "transaction_currency", "transaction_amount", "enriched_amount_usd",
    "card_present", "cardholder_present", "pan_entry_mode",
    "terminal_id", "authentication",
    "cvv2_result",          # MATCH | NOT_PROVIDED | NOT_APPLICABLE (POS/ATM)
    "avs_result",           # FULL_MATCH | PARTIAL_MATCH | NOT_PERFORMED
    "is_fraud",             # label
]


def build_txn(
    card, merchant, ts: datetime,
    amount: float, txn_country: str, channel: str,
    txn_type: str, pan_entry_mode: str, card_present: int, cardholder_present: int,
    auth: str, cvv2_result: str, avs_result: str, is_fraud: int,
) -> dict:
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
        # USD equivalent at fixed synthetic rates — use this for cross-currency comparisons
        "enriched_amount_usd":    round(amount * FX_TO_USD.get(CURRENCIES.get(txn_country, "USD"), 1.0), 2),
        "card_present":           card_present,
        "cardholder_present":     cardholder_present,
        "pan_entry_mode":          pan_entry_mode,
        "terminal_id":            generate_id("term"),
        "authentication":         auth,
        "cvv2_result":            cvv2_result,
        "avs_result":             avs_result,
        "is_fraud":               is_fraud,
    }


def generate_normal_txn(card, merchant, prev_ts: datetime, amount_hist: list) -> dict:
    gap_seconds = random.randint(5 * 60, 180 * 60)
    ts          = prev_ts + timedelta(seconds=gap_seconds)
    txn_country = (
        card["home_country"] if random.random() < random.uniform(0.80, 0.95)
        else merchant["country"]
    )

    amount   = max(1.0, sample_amount_lognormal(amount_hist, card["card_type"]))
    channel  = merchant["channel"]
    txn_type = "withdrawal" if channel == "ATM" else "purchase"

    # Resolve pan_entry_mode from merchant terminal profile BEFORE risk scoring.
    # Normal transactions use the merchant's installed terminal type.
    pan_entry_mode = merchant["_entry_mode_profile"]

    # card_present and cardholder_present are independent.
    # Scenarios where they diverge in legitimate transactions:
    #   card_present=1, cardholder_present=0 — merchant-initiated recurring (MIT),
    #     standing order, or card-on-file charge without active cardholder session
    #   card_present=0, cardholder_present=1 — CNP transaction where cardholder
    #     is actively authenticated but physical card is not read
    if channel == "ATM":
        card_present, cardholder_present = 1, 1
    elif channel == "POS":
        card_present = 1
        cardholder_present = 0 if random.random() < 0.08 else 1
    else:  # ECOMMERCE
        card_present = 0
        cardholder_present = 0 if random.random() < 0.15 else 1

    # Risk score computed with entry mode — never stored
    _risk = compute_risk_score(
        mcc                = merchant["mcc"],
        channel            = channel,
        pan_entry_mode     = pan_entry_mode,
        home_country       = card["home_country"],
        txn_country        = txn_country,
        gap_seconds        = gap_seconds,
        watchlist_merchant = bool(merchant["_internal_watchlist"]),
    )

    # Auth is channel-driven with intentional overlap with fraud auth values
    # so no single auth value is a perfect predictor of is_fraud.
    # NONE appears at low base rates in normal txns (tap-and-go failures,
    # fallback modes) so the model must learn context, not just auth.
    if channel == "ATM":
        auth = random.choices(["PIN", "NONE"], weights=[0.93, 0.07])[0]
    elif channel == "POS":
        auth = random.choices(["PIN", "CVV2", "BIOMETRICS", "NONE"], weights=[0.70, 0.12, 0.10, 0.08])[0]
    else:  # ECOMMERCE
        auth = random.choices(["OTP", "BIOMETRICS", "CVV2", "NONE"], weights=[0.50, 0.32, 0.10, 0.08])[0]

    # CVV2: only meaningful for CNP (ECOMMERCE). POS/ATM use chip verification.
    if channel == "ECOMMERCE":
        # NOT_PROVIDED for card-on-file/MIT (cardholder not active)
        cvv2_result = "NOT_PROVIDED" if cardholder_present == 0 else "MATCH"
    else:
        cvv2_result = "NOT_APPLICABLE"

    # AVS: only available in USA/GBR and only for CNP channels
    if channel != "ECOMMERCE" or txn_country not in AVS_COUNTRIES:
        avs_result = "NOT_PERFORMED"
    elif cardholder_present == 0:
        # Card-on-file / MIT: billing address not re-verified
        avs_result = "NOT_PERFORMED"
    else:
        avs_result = random.choices(
            ["FULL_MATCH", "PARTIAL_MATCH"],
            weights=[0.82, 0.18]
        )[0]

    return build_txn(card, merchant, ts, amount, txn_country,
                     channel, txn_type, pan_entry_mode, card_present, cardholder_present,
                     auth, cvv2_result, avs_result, is_fraud=0)


def generate_fraud_txn(card, merchant, prev_ts: datetime, amount_hist: list) -> dict:
    gap_seconds = random.randint(5, 120)
    ts          = prev_ts + timedelta(seconds=gap_seconds)
    txn_country = random.choice(list(COUNTRY_CITY_MAP.keys()))

    # Risk score computed after pan_entry_mode is resolved — never stored
    # (called at end of function once pan_entry_mode is known)
    pass  # risk call moved below channel/entry_mode resolution

    baseline = (
        float(np.exp(np.mean(np.log(np.maximum(amount_hist, 1)))))
        if len(amount_hist) >= 3 else 50.0
    )
    amount  = round(max(baseline * random.uniform(3, 8), float(np.random.uniform(200, 1200))), 2)
    channel = random.choices(["ECOMMERCE", "POS", "ATM"], weights=[0.6, 0.3, 0.1])[0]

    # Resolve pan_entry_mode BEFORE presence/auth decisions.
    # Fraud transactions are biased toward weaker entry modes:
    #   ATM/POS: magstripe-heavy (skimming), contactless (stolen card tap)
    #   ECOMMERCE: always ONLINE (CNP)
    # The entry mode then drives cardholder_present and auth:
    #   MAGSTRIPE  — skimmed card, cardholder definitely absent, no PIN needed
    #   CHIP       — stolen physical card + PIN compromise (rare)
    #   CONTACTLESS— stolen card tap-and-go, cardholder absent
    if channel == "ATM":
        txn_type     = "withdrawal"
        card_present = 1
        pan_entry_mode = random.choices(
            ["MAGSTRIPE", "CONTACTLESS", "CHIP"],
            weights=[0.65, 0.20, 0.15]   # skimming dominates ATM fraud
        )[0]
        if pan_entry_mode == "CHIP":
            # Chip+ATM fraud = stolen card + observed PIN — cardholder sometimes present (mule)
            cardholder_present = 0 if random.random() < 0.45 else 1
            auth = random.choices(["PIN", "NONE"], weights=[0.65, 0.35])[0]
        elif pan_entry_mode == "CONTACTLESS":
            # Contactless: stolen card, no PIN required
            cardholder_present = 0 if random.random() < 0.85 else 1
            auth = "NONE"
        else:  # MAGSTRIPE — skimmed card, fraudster fully remote
            cardholder_present = 0 if random.random() < 0.95 else 1
            auth = random.choices(["NONE", "PIN"], weights=[0.75, 0.25])[0]

    elif channel == "POS":
        txn_type     = "purchase"
        card_present = 1
        pan_entry_mode = random.choices(
            ["MAGSTRIPE", "CONTACTLESS", "CHIP"],
            weights=[0.40, 0.40, 0.20]   # both skimming and tap-and-go common at POS
        )[0]
        if pan_entry_mode == "CHIP":
            cardholder_present = 0 if random.random() < 0.50 else 1
            auth = random.choices(["PIN", "NONE", "CVV2"], weights=[0.45, 0.40, 0.15])[0]
        elif pan_entry_mode == "CONTACTLESS":
            cardholder_present = 0 if random.random() < 0.80 else 1
            auth = random.choices(["NONE", "PIN"], weights=[0.70, 0.30])[0]
        else:  # MAGSTRIPE
            cardholder_present = 0 if random.random() < 0.90 else 1
            auth = random.choices(["NONE", "PIN", "CVV2"], weights=[0.60, 0.25, 0.15])[0]

    else:  # ECOMMERCE — CNP, no physical entry mode
        txn_type, card_present, cardholder_present = "purchase", 0, 0
        pan_entry_mode = "ONLINE"
        auth = random.choices(["NONE", "CVV2", "OTP", "BIOMETRICS"], weights=[0.60, 0.28, 0.08, 0.04])[0]

    # CVV2 for fraud: ECOMMERCE only. Fraudsters rarely have CVV2 → NOT_PROVIDED skewed higher.
    if channel == "ECOMMERCE":
        cvv2_result = random.choices(
            ["MATCH", "NOT_PROVIDED"],
            weights=[0.20, 0.80]   # fraudsters rarely have the real CVV2
        )[0]
    else:
        cvv2_result = "NOT_APPLICABLE"

    # AVS for fraud: skewed toward PARTIAL_MATCH and NOT_PERFORMED
    if channel != "ECOMMERCE" or txn_country not in AVS_COUNTRIES:
        avs_result = "NOT_PERFORMED"
    else:
        avs_result = random.choices(
            ["FULL_MATCH", "PARTIAL_MATCH", "NOT_PERFORMED"],
            weights=[0.10, 0.45, 0.45]   # fraudsters rarely have full billing address
        )[0]

    _risk = compute_risk_score(
        mcc                = merchant["mcc"],
        channel            = channel,
        pan_entry_mode     = pan_entry_mode,
        home_country       = card["home_country"],
        txn_country        = txn_country,
        gap_seconds        = gap_seconds,
        watchlist_merchant = bool(merchant["_internal_watchlist"]),
    )

    return build_txn(card, merchant, ts, amount, txn_country,
                     channel, txn_type, pan_entry_mode, card_present, cardholder_present,
                     auth, cvv2_result, avs_result, is_fraud=1)

# =============================================================================
# MAIN
# =============================================================================
def generate_dataset():
    merchants = generate_merchants()
    cards     = generate_cards()

    merchant_weights = merchants["_weight"].values.copy()

    # MCC-biased weights for fraud merchant sampling.
    # Multiplies the Zipf sampling weight by the MCC fraud propensity score,
    # then renormalises — high-risk MCC merchants are proportionally more
    # likely to be the merchant in a fraud transaction.
    mcc_bias   = merchants["mcc"].map(MCC_FRAUD_WEIGHT).fillna(1.0).values
    # Also bias toward merchants with magstripe terminals (skimming target)
    entry_bias = merchants["_entry_mode_profile"].map(PAN_ENTRY_FRAUD_WEIGHT).fillna(1.0).values
    raw_fraud_weights = merchant_weights * mcc_bias * entry_bias
    merchant_fraud_weights = raw_fraud_weights / raw_fraud_weights.sum()
    card_ids         = list(cards["card_id"])
    n_cards          = len(cards)

    # Pre-allocate txn counts so sum == N_TRANSACTIONS exactly
    raw_counts = np.array([random.randint(10, 40) for _ in range(n_cards)], dtype=float)
    scaled     = raw_counts / raw_counts.sum() * N_TRANSACTIONS
    txn_counts = np.floor(scaled).astype(int)
    remainder  = N_TRANSACTIONS - txn_counts.sum()
    if remainder > 0:
        txn_counts[np.argsort(scaled - txn_counts)[::-1][:remainder]] += 1
    txn_counts = np.maximum(txn_counts, 1)

    # Weight fraud slot assignment by card type propensity
    card_type_bias = cards["card_type"].map(CARD_TYPE_FRAUD_WEIGHT).fillna(1.0).values
    card_type_weights = dict(zip(card_ids, card_type_bias))
    fraud_alloc = assign_fraud_slots(card_ids, TARGET_FRAUD,
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
            if is_fraud_txn:
                # Fraud disproportionately occurs at high-risk MCC merchants.
                # Sample using MCC-biased weights so the MCC↔fraud correlation
                # emerges naturally in the data rather than being random noise.
                merchant = sample_merchant(merchants, merchant_fraud_weights)
            else:
                merchant = sample_merchant(merchants, merchant_weights)
            txn = (
                generate_fraud_txn(card, merchant, prev_ts, amount_hist)
                if is_fraud_txn else
                generate_normal_txn(card, merchant, prev_ts, amount_hist)
            )
            amount_hist.append(txn["transaction_amount"])
            if len(amount_hist) > 20:
                amount_hist = amount_hist[-20:]
            prev_ts = datetime.fromisoformat(txn["timestamp"])
            txns.append(txn)

    df = pd.DataFrame(txns)
    assert len(df) == N_TRANSACTIONS, f"Row count mismatch: {len(df)} != {N_TRANSACTIONS}"

    # Enforce output column contract — no internal fields can sneak through
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
    df.to_csv(raw_dir / "transactions.csv", index=False)
    print(f"\nSaved to {raw_dir / 'transactions.csv'}")

if __name__ == "__main__":
    generate_dataset()