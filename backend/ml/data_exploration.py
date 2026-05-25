import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from src.config import DATA_DIR


# -----------------------------
# Config
# -----------------------------
DATA_PATH     = f"{DATA_DIR}/raw/transactions.csv"
OUTPUT_TABLES = f"{DATA_DIR}/eda_outputs/tables"
OUTPUT_PLOTS  = f"{DATA_DIR}/eda_outputs/plots"

# Consistent palette: index 0 = legitimate, index 1 = fraud
PALETTE = {0: "#4C72B0", 1: "#DD3A3A"}
LABEL_MAP = {0: "Legitimate", 1: "Fraud"}


# MCC code → human-readable description
# Covers all codes present in the generator (HIGH_RISK + LOW_RISK MCCs)
MCC_LABELS = {
    "7995": "Gambling / Crypto",
    "4829": "Money Transfer / Wire",
    "6012": "Financial Institution",
    "5933": "Pawn / Secondhand",
    "5542": "Fuel / Unmanned POS",
    "5732": "Electronics",
    "5651": "Clothing / Apparel",
    "5814": "Fast Food",
    "5812": "Restaurants",
    "5411": "Grocery",
    "5541": "Service Stations",
    "5311": "Department Stores",
    "5999": "Misc Retail",
}

# -----------------------------
# Setup
# -----------------------------
def create_output_dirs():
    os.makedirs(OUTPUT_TABLES, exist_ok=True)
    os.makedirs(OUTPUT_PLOTS, exist_ok=True)


# -----------------------------
# Load Data
# -----------------------------
# Columns that must exist in the CSV.
# If any are missing the CSV is stale — re-run dataset_generator.py to regenerate it.
# enriched_amount_usd is a derived field (ISO 8583 DE 4 = transaction_amount).
REQUIRED_COLUMNS = {
    "transaction_amount",       # ISO 8583 DE 4
    "transaction_currency",     # ISO 8583 DE 49
    "transaction_country",      # transaction location
    "enriched_amount_usd",      # derived: transaction_amount converted to USD at fixed rates
    "cvv2_result",
    "avs_result",
    "card_type",
    "pan_entry_mode",
    "is_fraud",                 # label
}

def load_data(path):
    df = pd.read_csv(path)
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise KeyError(
            f"CSV is missing columns: {missing}\n"
            f"The CSV on disk is likely stale. Re-run dataset_generator.py to regenerate it."
        )
    return df


# -----------------------------
# Basic Info
# -----------------------------
def save_basic_info(df):
    with open(f"{OUTPUT_TABLES}/info.txt", "w") as f:
        f.write(str(df.info()))
    df.describe().to_csv(f"{OUTPUT_TABLES}/describe.csv")


# -----------------------------
# Preprocessing (light for EDA)
# -----------------------------
def preprocess(df):
    df = df.copy()
    df['timestamp']   = pd.to_datetime(df['timestamp'])
    df['hour']        = df['timestamp'].dt.hour
    df['day_of_week'] = df['timestamp'].dt.dayofweek
    df['is_weekend']  = df['day_of_week'].isin([5, 6]).astype(int)
    df['cross_border'] = (
        df['issuing_bank_country'] != df['transaction_country']
    ).astype(int)
    return df


# -----------------------------
# Helpers
# -----------------------------
def _save(fig, name):
    fig.savefig(f"{OUTPUT_PLOTS}/{name}.png", bbox_inches="tight", dpi=150)
    plt.close(fig)

def _fraud_label(val):
    return LABEL_MAP.get(val, str(val))


# -----------------------------
# Fraud Distribution
# -----------------------------
def analyze_fraud_distribution(df):
    fraud_dist = df['is_fraud'].value_counts(normalize=True).sort_index()
    fraud_dist.to_csv(f"{OUTPUT_TABLES}/fraud_distribution.csv")

    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar(
        [_fraud_label(i) for i in fraud_dist.index],
        fraud_dist.values,
        color=[PALETTE[i] for i in fraud_dist.index],
        width=0.5, edgecolor="white"
    )
    for bar, val in zip(bars, fraud_dist.values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.005,
                f"{val:.1%}", ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax.set_title("Transaction Class Distribution", fontsize=13, fontweight="bold")
    ax.set_ylabel("Proportion")
    ax.set_ylim(0, 1.1)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))
    sns.despine(ax=ax)
    _save(fig, "fraud_distribution")


# -----------------------------
# Amount Analysis — enriched_amount_usd
# Violin + strip plot: shows distribution shape AND outlier spread
# -----------------------------
def analyze_amount(df):
    # Stats on the USD-normalised amount (cross-currency comparable)
    usd_stats = df.groupby('is_fraud')['enriched_amount_usd'].describe()
    usd_stats.to_csv(f"{OUTPUT_TABLES}/enriched_amount_usd_by_fraud.csv")

    plot_df = df[['enriched_amount_usd', 'is_fraud']].copy()
    plot_df['label'] = plot_df['is_fraud'].map(_fraud_label)

    # --- Plot 1: Violin on log scale ---
    fig, ax = plt.subplots(figsize=(7, 5))
    sns.violinplot(
        x='label', y='enriched_amount_usd', data=plot_df,
        palette=list(PALETTE.values()), inner="box",
        order=[_fraud_label(0), _fraud_label(1)], ax=ax
    )
    ax.set_yscale('log')
    ax.set_title("Transaction Amount (USD) by Fraud Label", fontsize=13, fontweight="bold")
    ax.set_xlabel("")
    ax.set_ylabel("Amount USD (log scale)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    sns.despine(ax=ax)
    _save(fig, "amount_violin_log")

    # --- Plot 2: Overlapping KDE on log scale ---
    fig, ax = plt.subplots(figsize=(8, 4))
    for label, grp in df.groupby('is_fraud'):
        vals = np.log10(grp['enriched_amount_usd'].clip(lower=0.01))
        vals.plot.kde(ax=ax, label=_fraud_label(label),
                      color=PALETTE[label], linewidth=2)
    ax.set_title("USD Amount Distribution by Fraud Label (log₁₀ scale)",
                 fontsize=13, fontweight="bold")
    ax.set_xlabel("log₁₀(Amount USD)")
    ax.set_ylabel("Density")
    ax.legend(title="Class")
    sns.despine(ax=ax)
    _save(fig, "amount_kde_log")


# -----------------------------
# Channel Analysis
# -----------------------------
def analyze_channel(df):
    channel_fraud = df.groupby('channel')['is_fraud'].mean().sort_values()
    channel_counts = df.groupby('channel')['is_fraud'].count()
    channel_fraud.to_csv(f"{OUTPUT_TABLES}/channel_fraud_rate.csv")

    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.barh(
        channel_fraud.index, channel_fraud.values,
        color=sns.color_palette("Blues_d", len(channel_fraud)),
        edgecolor="white"
    )
    for bar, (ch, val) in zip(bars, channel_fraud.items()):
        n = channel_counts[ch]
        ax.text(val + 0.001, bar.get_y() + bar.get_height() / 2,
                f"  {val:.1%}  (n={n:,})", va="center", fontsize=9)
    ax.set_title("Fraud Rate by Channel", fontsize=13, fontweight="bold")
    ax.set_xlabel("Fraud Rate")
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))
    ax.set_xlim(0, channel_fraud.max() * 1.5)
    sns.despine(ax=ax)
    _save(fig, "channel_fraud")


# -----------------------------
# Cross-Border Analysis
# Grouped bar: volume + fraud rate together
# -----------------------------
def analyze_cross_border(df):
    cb = df.groupby('cross_border').agg(
        count=('is_fraud', 'count'),
        fraud_rate=('is_fraud', 'mean')
    ).reset_index()
    cb.to_csv(f"{OUTPUT_TABLES}/cross_border_fraud.csv")

    cb['label'] = cb['cross_border'].map({0: "Domestic", 1: "Cross-Border"})

    fig, ax1 = plt.subplots(figsize=(6, 4))
    ax2 = ax1.twinx()

    x = range(len(cb))
    ax1.bar(x, cb['count'], color=[PALETTE[0], PALETTE[1]],
            alpha=0.6, width=0.5, label="Volume")
    ax2.plot(x, cb['fraud_rate'], 'o--', color='black',
             linewidth=1.5, markersize=8, label="Fraud Rate")

    ax1.set_xticks(list(x))
    ax1.set_xticklabels(cb['label'])
    ax1.set_ylabel("Transaction Count")
    ax2.set_ylabel("Fraud Rate")
    ax2.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))
    ax1.set_title("Cross-Border: Volume vs Fraud Rate", fontsize=13, fontweight="bold")

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=9)
    sns.despine(ax=ax1, right=False)
    _save(fig, "cross_border_fraud")


# -----------------------------
# Authentication Analysis
# Dot plot with sample size annotation
# -----------------------------
def analyze_authentication(df):
    auth_stats = df.groupby('authentication').agg(
        fraud_rate=('is_fraud', 'mean'),
        count=('is_fraud', 'count')
    ).sort_values('fraud_rate')
    auth_stats.to_csv(f"{OUTPUT_TABLES}/auth_fraud.csv")

    fig, ax = plt.subplots(figsize=(7, 4))
    colors = [PALETTE[1] if r > df['is_fraud'].mean() else PALETTE[0]
              for r in auth_stats['fraud_rate']]
    ax.hlines(auth_stats.index, 0, auth_stats['fraud_rate'],
              color='lightgrey', linewidth=1.5, zorder=1)
    ax.scatter(auth_stats['fraud_rate'], auth_stats.index,
               color=colors, s=120, zorder=2)
    for auth, row in auth_stats.iterrows():
        ax.text(row['fraud_rate'] + 0.001, auth,
                f"  {row['fraud_rate']:.1%}  (n={int(row['count']):,})",
                va="center", fontsize=9)
    avg = df['is_fraud'].mean()
    ax.axvline(avg, color='grey', linestyle='--', linewidth=1, label=f"Overall avg {avg:.1%}")
    ax.set_title("Fraud Rate by Authentication Method", fontsize=13, fontweight="bold")
    ax.set_xlabel("Fraud Rate")
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))
    ax.set_xlim(0, auth_stats['fraud_rate'].max() * 1.6)
    ax.legend(fontsize=9)
    sns.despine(ax=ax)
    _save(fig, "auth_fraud")


# -----------------------------
# MCC Analysis
# Lollipop: fraud rate by readable MCC description
# Grouped bar: volume split by fraud/legitimate per MCC
# -----------------------------
def analyze_mcc(df):
    # Map codes to labels; fall back to raw code if unmapped
    df = df.copy()
    df['mcc_label'] = df['merchant_category_code'].astype(str).map(MCC_LABELS).fillna(
        df['merchant_category_code'].astype(str)
    )

    mcc_stats = df.groupby('mcc_label').agg(
        fraud_rate=('is_fraud', 'mean'),
        total=('is_fraud', 'count'),
        fraud_count=('is_fraud', 'sum'),
    )
    mcc_stats['legit_count'] = mcc_stats['total'] - mcc_stats['fraud_count']
    mcc_stats = mcc_stats.sort_values('fraud_rate', ascending=True)
    mcc_stats.to_csv(f"{OUTPUT_TABLES}/mcc_fraud.csv")

    avg = df['is_fraud'].mean()

    # --- Plot 1: Lollipop — fraud rate per MCC description ---
    fig, ax = plt.subplots(figsize=(9, 6))
    colors = [PALETTE[1] if r > avg else PALETTE[0] for r in mcc_stats['fraud_rate']]
    ax.hlines(mcc_stats.index, 0, mcc_stats['fraud_rate'],
              color='lightgrey', linewidth=1.5, zorder=1)
    ax.scatter(mcc_stats['fraud_rate'], mcc_stats.index,
               color=colors, s=120, zorder=2)
    for label, row in mcc_stats.iterrows():
        ax.text(row['fraud_rate'] + 0.0005, label,
                f"  {row['fraud_rate']:.1%}  (n={int(row['total']):,})",
                va="center", fontsize=8.5)
    ax.axvline(avg, color='grey', linestyle='--', linewidth=1,
               label=f"Overall avg {avg:.1%}")
    ax.set_title("Fraud Rate by Merchant Category", fontsize=13, fontweight="bold")
    ax.set_xlabel("Fraud Rate")
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))
    ax.set_xlim(0, mcc_stats['fraud_rate'].max() * 1.55)
    ax.legend(fontsize=9)
    sns.despine(ax=ax)
    _save(fig, "mcc_fraud_rate")

    # --- Plot 2: Stacked bar — volume breakdown per MCC ---
    mcc_vol = mcc_stats.sort_values('total', ascending=True)
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(mcc_vol.index, mcc_vol['legit_count'],
            color=PALETTE[0], label="Legitimate", edgecolor="white")
    ax.barh(mcc_vol.index, mcc_vol['fraud_count'],
            left=mcc_vol['legit_count'],
            color=PALETTE[1], label="Fraud", edgecolor="white")
    for label, row in mcc_vol.iterrows():
        ax.text(row['total'] + 20, label,
                f"  {row['fraud_rate']:.1%} fraud",
                va="center", fontsize=8.5, color=PALETTE[1])
    ax.set_title("Transaction Volume by Merchant Category", fontsize=13, fontweight="bold")
    ax.set_xlabel("Transaction Count")
    ax.legend(loc="lower right", fontsize=9)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    sns.despine(ax=ax)
    _save(fig, "mcc_volume")


# -----------------------------
# Time Analysis
# Bar chart by hour with smoothed trend overlay
# -----------------------------
def analyze_time(df):
    hour_stats = df.groupby('hour').agg(
        fraud_rate=('is_fraud', 'mean'),
        count=('is_fraud', 'count')
    )
    hour_stats.to_csv(f"{OUTPUT_TABLES}/hour_fraud.csv")

    fig, ax1 = plt.subplots(figsize=(10, 4))
    ax2 = ax1.twinx()

    ax1.bar(hour_stats.index, hour_stats['count'],
            color=PALETTE[0], alpha=0.4, label="Transaction Volume")
    ax2.plot(hour_stats.index, hour_stats['fraud_rate'],
             color=PALETTE[1], linewidth=2, marker='o', markersize=4, label="Fraud Rate")
    avg = df['is_fraud'].mean()
    ax2.axhline(avg, color='grey', linestyle='--', linewidth=1, label=f"Overall avg {avg:.1%}")

    ax1.set_xlabel("Hour of Day")
    ax1.set_ylabel("Transaction Count")
    ax2.set_ylabel("Fraud Rate")
    ax2.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))
    ax1.set_xticks(range(0, 24))
    ax1.set_title("Fraud Rate and Volume by Hour of Day", fontsize=13, fontweight="bold")

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=9)
    sns.despine(ax=ax1, right=False)
    _save(fig, "hour_fraud")


# -----------------------------
# Correlation Analysis
# Fixed: full labels, annotated values, drop transaction_amount in favour of enriched_amount_usd
# -----------------------------
def analyze_correlation(df):
    # Drop transaction_amount (near-duplicate of enriched_amount_usd — differs only by FX rate)
    # Drop merchant_category_code (categorical identifier, not ordinal — numeric correlation is meaningless)
    drop_cols = ['transaction_amount', 'merchant_category_code']  # categorical — not ordinal
    num_cols = df.select_dtypes(include=np.number).drop(
        columns=[c for c in drop_cols if c in df.columns]
    )

    corr = num_cols.corr()
    corr.to_csv(f"{OUTPUT_TABLES}/correlation.csv")

    n = len(corr)
    fig_size = max(10, n * 0.9)
    fig, ax = plt.subplots(figsize=(fig_size, fig_size * 0.85))

    mask = np.zeros_like(corr, dtype=bool)
    mask[np.triu_indices_from(mask, k=1)] = True  # upper triangle only

    sns.heatmap(
        corr,
        mask=mask,
        annot=True,
        fmt=".2f",
        cmap="coolwarm",
        center=0,
        vmin=-1, vmax=1,
        linewidths=0.5,
        linecolor="white",
        annot_kws={"size": 8},
        ax=ax,
        cbar_kws={"shrink": 0.8, "label": "Pearson r"},
    )

    # Full label display — no truncation
    ax.set_xticklabels(
        ax.get_xticklabels(), rotation=45, ha="right", fontsize=9
    )
    ax.set_yticklabels(
        ax.get_yticklabels(), rotation=0, fontsize=9
    )
    ax.set_title("Correlation Matrix (lower triangle)", fontsize=13, fontweight="bold", pad=14)
    fig.tight_layout()
    _save(fig, "correlation")


# -----------------------------
# CVV2 Result Analysis
# -----------------------------
def analyze_cvv2(df):
    # Exclude NOT_APPLICABLE (POS/ATM) — only CNP rows are meaningful
    cnp = df[df['cvv2_result'] != 'NOT_APPLICABLE'].copy()

    stats = cnp.groupby('cvv2_result').agg(
        fraud_rate=('is_fraud', 'mean'),
        count=('is_fraud', 'count')
    ).sort_values('fraud_rate')
    stats.to_csv(f"{OUTPUT_TABLES}/cvv2_fraud.csv")

    avg = cnp['is_fraud'].mean()
    fig, ax = plt.subplots(figsize=(7, 3))
    colors = [PALETTE[1] if r > avg else PALETTE[0] for r in stats['fraud_rate']]
    ax.hlines(stats.index, 0, stats['fraud_rate'], color='lightgrey', linewidth=1.5, zorder=1)
    ax.scatter(stats['fraud_rate'], stats.index, color=colors, s=120, zorder=2)
    for val, row in stats.iterrows():
        ax.text(row['fraud_rate'] + 0.001, val,
                f"  {row['fraud_rate']:.1%}  (n={int(row['count']):,})",
                va="center", fontsize=9)
    ax.axvline(avg, color='grey', linestyle='--', linewidth=1, label=f"CNP avg {avg:.1%}")
    ax.set_title("Fraud Rate by CVV2 Result (CNP only)", fontsize=13, fontweight="bold")
    ax.set_xlabel("Fraud Rate")
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))
    ax.set_xlim(0, stats['fraud_rate'].max() * 1.6)
    ax.legend(fontsize=9)
    sns.despine(ax=ax)
    _save(fig, "cvv2_fraud")


# -----------------------------
# AVS Result Analysis
# -----------------------------
def analyze_avs(df):
    # NOT_PERFORMED dominates outside USA/GBR — separate performed vs not
    performed = df[df['avs_result'] != 'NOT_PERFORMED'].copy()

    # Full dataset breakdown (all values)
    all_stats = df.groupby('avs_result').agg(
        fraud_rate=('is_fraud', 'mean'),
        count=('is_fraud', 'count')
    ).sort_values('fraud_rate')
    all_stats.to_csv(f"{OUTPUT_TABLES}/avs_fraud.csv")

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    # Left: all values including NOT_PERFORMED
    avg_all = df['is_fraud'].mean()
    colors = [PALETTE[1] if r > avg_all else PALETTE[0] for r in all_stats['fraud_rate']]
    axes[0].hlines(all_stats.index, 0, all_stats['fraud_rate'],
                   color='lightgrey', linewidth=1.5, zorder=1)
    axes[0].scatter(all_stats['fraud_rate'], all_stats.index,
                    color=colors, s=120, zorder=2)
    for val, row in all_stats.iterrows():
        axes[0].text(row['fraud_rate'] + 0.001, val,
                     f"  {row['fraud_rate']:.1%}  (n={int(row['count']):,})",
                     va="center", fontsize=9)
    axes[0].axvline(avg_all, color='grey', linestyle='--', linewidth=1,
                    label=f"Overall avg {avg_all:.1%}")
    axes[0].set_title("All Transactions", fontsize=11, fontweight="bold")
    axes[0].set_xlabel("Fraud Rate")
    axes[0].xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))
    axes[0].set_xlim(0, all_stats['fraud_rate'].max() * 1.6)
    axes[0].legend(fontsize=8)
    sns.despine(ax=axes[0])

    # Right: AVS-performed only (USA/GBR ECOMMERCE)
    if len(performed) > 0:
        perf_stats = performed.groupby('avs_result').agg(
            fraud_rate=('is_fraud', 'mean'),
            count=('is_fraud', 'count')
        ).sort_values('fraud_rate')
        avg_perf = performed['is_fraud'].mean()
        colors2 = [PALETTE[1] if r > avg_perf else PALETTE[0] for r in perf_stats['fraud_rate']]
        axes[1].hlines(perf_stats.index, 0, perf_stats['fraud_rate'],
                       color='lightgrey', linewidth=1.5, zorder=1)
        axes[1].scatter(perf_stats['fraud_rate'], perf_stats.index,
                        color=colors2, s=120, zorder=2)
        for val, row in perf_stats.iterrows():
            axes[1].text(row['fraud_rate'] + 0.001, val,
                         f"  {row['fraud_rate']:.1%}  (n={int(row['count']):,})",
                         va="center", fontsize=9)
        axes[1].axvline(avg_perf, color='grey', linestyle='--', linewidth=1,
                        label=f"AVS-performed avg {avg_perf:.1%}")
        axes[1].set_title("AVS-Performed Only (USA/GBR ECOMMERCE)", fontsize=11, fontweight="bold")
        axes[1].set_xlabel("Fraud Rate")
        axes[1].xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))
        axes[1].set_xlim(0, perf_stats['fraud_rate'].max() * 1.6)
        axes[1].legend(fontsize=8)
        sns.despine(ax=axes[1])

    fig.suptitle("Fraud Rate by AVS Result", fontsize=13, fontweight="bold")
    fig.tight_layout()
    _save(fig, "avs_fraud")



# -----------------------------
# Card Type Analysis
# Three views: fraud rate, volume breakdown, amount distribution
# -----------------------------
def analyze_card_type(df):
    stats = df.groupby('card_type').agg(
        fraud_rate=('is_fraud', 'mean'),
        total=('is_fraud', 'count'),
        fraud_count=('is_fraud', 'sum'),
    ).sort_values('fraud_rate', ascending=True)
    stats['legit_count'] = stats['total'] - stats['fraud_count']
    stats.to_csv(f"{OUTPUT_TABLES}/card_type_fraud.csv")

    avg = df['is_fraud'].mean()

    fig, axes = plt.subplots(1, 3, figsize=(15, 4))

    # --- Panel 1: Fraud rate lollipop ---
    colors = [PALETTE[1] if r > avg else PALETTE[0] for r in stats['fraud_rate']]
    axes[0].hlines(stats.index, 0, stats['fraud_rate'],
                   color='lightgrey', linewidth=1.5, zorder=1)
    axes[0].scatter(stats['fraud_rate'], stats.index,
                    color=colors, s=140, zorder=2)
    for ct, row in stats.iterrows():
        axes[0].text(row['fraud_rate'] + 0.001, ct,
                     f"  {row['fraud_rate']:.1%}  (n={int(row['total']):,})",
                     va='center', fontsize=9)
    axes[0].axvline(avg, color='grey', linestyle='--', linewidth=1,
                    label=f"Overall avg {avg:.1%}")
    axes[0].set_title("Fraud Rate by Card Type", fontsize=11, fontweight="bold")
    axes[0].set_xlabel("Fraud Rate")
    axes[0].xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))
    axes[0].set_xlim(0, stats['fraud_rate'].max() * 1.6)
    axes[0].legend(fontsize=8)
    sns.despine(ax=axes[0])

    # --- Panel 2: Stacked volume bar ---
    vol = stats.sort_values('total', ascending=True)
    axes[1].barh(vol.index, vol['legit_count'],
                 color=PALETTE[0], label="Legitimate", edgecolor="white")
    axes[1].barh(vol.index, vol['fraud_count'], left=vol['legit_count'],
                 color=PALETTE[1], label="Fraud", edgecolor="white")
    for ct, row in vol.iterrows():
        axes[1].text(row['total'] + 20, ct,
                     f"  {row['fraud_rate']:.1%} fraud",
                     va='center', fontsize=8.5, color=PALETTE[1])
    axes[1].set_title("Volume by Card Type", fontsize=11, fontweight="bold")
    axes[1].set_xlabel("Transaction Count")
    axes[1].legend(loc="lower right", fontsize=8)
    axes[1].xaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    sns.despine(ax=axes[1])

    # --- Panel 3: USD amount KDE by card type ---
    card_type_colors = {"Debit": "#4C72B0", "Credit": "#55A868", "Prepaid": "#DD3A3A"}
    for ct, grp in df.groupby('card_type'):
        vals = np.log10(grp['enriched_amount_usd'].clip(lower=0.01))
        vals.plot.kde(ax=axes[2], label=ct,
                      color=card_type_colors.get(ct, 'grey'), linewidth=2)
    axes[2].set_title("USD Amount Distribution by Card Type", fontsize=11, fontweight="bold")
    axes[2].set_xlabel("log₁₀(Amount USD)")
    axes[2].set_ylabel("Density")
    axes[2].legend(title="Card Type", fontsize=8)
    sns.despine(ax=axes[2])

    fig.suptitle("Card Type Analysis", fontsize=13, fontweight="bold", y=1.02)
    fig.tight_layout()
    _save(fig, "card_type_analysis")

    # --- Supplementary: fraud amount by card type — violin ---
    fig, ax = plt.subplots(figsize=(8, 5))
    plot_df = df.copy()
    plot_df['label'] = plot_df['is_fraud'].map(_fraud_label)
    sns.violinplot(
        x='card_type', y='enriched_amount_usd', hue='label',
        data=plot_df, palette=list(PALETTE.values()),
        inner="box", split=False, ax=ax
    )
    ax.set_yscale('log')
    ax.set_title("USD Amount by Card Type and Fraud Label", fontsize=13, fontweight="bold")
    ax.set_xlabel("Card Type")
    ax.set_ylabel("Amount USD (log scale)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.legend(title="Class", fontsize=9)
    sns.despine(ax=ax)
    _save(fig, "card_type_amount_violin")


# -----------------------------
# PAN Entry Mode Analysis
# Fraud rate by entry mode + channel × entry mode heatmap
# -----------------------------
def analyze_pan_entry_mode(df):
    stats = df.groupby('pan_entry_mode').agg(
        fraud_rate=('is_fraud', 'mean'),
        total=('is_fraud', 'count'),
        fraud_count=('is_fraud', 'sum'),
    ).sort_values('fraud_rate', ascending=True)
    stats.to_csv(f"{OUTPUT_TABLES}/pan_entry_mode_fraud.csv")

    avg = df['is_fraud'].mean()

    fig, axes = plt.subplots(1, 2, figsize=(13, 4))

    # --- Panel 1: Lollipop fraud rate per entry mode ---
    colors = [PALETTE[1] if r > avg else PALETTE[0] for r in stats['fraud_rate']]
    axes[0].hlines(stats.index, 0, stats['fraud_rate'],
                   color='lightgrey', linewidth=1.5, zorder=1)
    axes[0].scatter(stats['fraud_rate'], stats.index,
                    color=colors, s=140, zorder=2)
    for em, row in stats.iterrows():
        axes[0].text(row['fraud_rate'] + 0.001, em,
                     f"  {row['fraud_rate']:.1%}  (n={int(row['total']):,})",
                     va='center', fontsize=9)
    axes[0].axvline(avg, color='grey', linestyle='--', linewidth=1,
                    label=f"Overall avg {avg:.1%}")
    axes[0].set_title("Fraud Rate by PAN Entry Mode", fontsize=11, fontweight="bold")
    axes[0].set_xlabel("Fraud Rate")
    axes[0].xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))
    axes[0].set_xlim(0, stats['fraud_rate'].max() * 1.6)
    axes[0].legend(fontsize=8)
    sns.despine(ax=axes[0])

    # --- Panel 2: Channel × entry mode fraud rate heatmap ---
    pivot = df.groupby(['channel', 'pan_entry_mode'])['is_fraud'].mean().unstack(fill_value=0)
    sns.heatmap(
        pivot, annot=True, fmt=".1%", cmap="YlOrRd",
        linewidths=0.5, linecolor='white',
        cbar_kws={"label": "Fraud Rate", "format": mticker.PercentFormatter(xmax=1)},
        ax=axes[1]
    )
    axes[1].set_title("Fraud Rate: Channel × PAN Entry Mode", fontsize=11, fontweight="bold")
    axes[1].set_xlabel("PAN Entry Mode")
    axes[1].set_ylabel("Channel")
    axes[1].set_xticklabels(axes[1].get_xticklabels(), rotation=30, ha='right')
    axes[1].set_yticklabels(axes[1].get_yticklabels(), rotation=0)

    fig.suptitle("PAN Entry Mode Analysis", fontsize=13, fontweight="bold", y=1.02)
    fig.tight_layout()
    _save(fig, "pan_entry_mode_analysis")


# -----------------------------
# Card Type × Channel heatmap
# Fraud rate across the card_type / channel combination
# -----------------------------
def analyze_card_type_channel(df):
    pivot = df.groupby(['card_type', 'channel'])['is_fraud'].mean().unstack(fill_value=0)
    pivot.to_csv(f"{OUTPUT_TABLES}/card_type_channel_fraud.csv")

    fig, ax = plt.subplots(figsize=(7, 4))
    sns.heatmap(
        pivot, annot=True, fmt=".1%", cmap="YlOrRd",
        linewidths=0.5, linecolor='white',
        cbar_kws={"label": "Fraud Rate", "format": mticker.PercentFormatter(xmax=1)},
        ax=ax
    )
    ax.set_title("Fraud Rate: Card Type × Channel", fontsize=13, fontweight="bold")
    ax.set_xlabel("Channel")
    ax.set_ylabel("Card Type")
    ax.set_xticklabels(ax.get_xticklabels(), rotation=0)
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0)
    fig.tight_layout()
    _save(fig, "card_type_channel_heatmap")

# -----------------------------
# Main Runner
# -----------------------------
def run_eda():
    create_output_dirs()
    df = load_data(DATA_PATH)
    save_basic_info(df)
    df = preprocess(df)

    analyze_fraud_distribution(df)
    analyze_amount(df)
    analyze_channel(df)
    analyze_cross_border(df)
    analyze_authentication(df)
    analyze_mcc(df)
    analyze_time(df)
    analyze_cvv2(df)
    analyze_avs(df)
    analyze_card_type(df)
    analyze_pan_entry_mode(df)
    analyze_card_type_channel(df)
    analyze_correlation(df)

    print("EDA completed. Outputs saved.")


# -----------------------------
# Entry Point
# -----------------------------
if __name__ == "__main__":
    run_eda()