# Model Evaluation

Training and evaluation results for the FraudPulse fraud-scoring model.

The model in production is the **Tuned Calibrated LightGBM (version 2)**. The backend loads it from `ml/artefacts/version2/` — see `src/core/config.py` (`ML_ARTEFACTS_DIR`) and `src/services/scoring_service.py`.

---

## 1. Production model — Tuned Calibrated LightGBM (v2)

### Dataset

| Split             | Rows   |
| ----------------- | ------ |
| Training          | 45,333 |
| Validation        | 9,714  |
| Calibration       | 9,715  |
| **Total training**| 64,762 |
| **Held-out test** | 16,190 |

32 features. Fraud prevalence in the test set: 534 / 16,190 (3.3%).

### Performance on the held-out test set

Classification metrics at a raw 0.50 probability cut:

| Metric            | Fraud class | Non-fraud class |
| ----------------- | ----------- | --------------- |
| Precision         | 0.731       | 0.986           |
| Recall            | 0.590       | 0.993           |
| F1-score          | 0.653       | 0.989           |
| Support           | 534         | 15,656          |

| Overall metric | Value  |
| -------------- | ------ |
| Accuracy       | 0.979  |
| ROC-AUC        | 0.966  |
| PR-AUC         | 0.721  |
| Best validation PR-AUC (tuning) | 0.750 |

Confusion matrix at 0.50:

|                    | Predicted legit | Predicted fraud |
| ------------------ | --------------- | --------------- |
| **Actually legit** | 15,540          | 116             |
| **Actually fraud** | 219             | 315             |

PR-AUC is the metric to read here, not accuracy — at 3.3% fraud prevalence, a model that approved everything would still score 96.7% accuracy.

### Best hyperparameters

Selected by randomised search on validation PR-AUC:

```json
{
  "n_estimators": 300,
  "learning_rate": 0.08,
  "num_leaves": 15,
  "max_depth": 12,
  "min_child_samples": 100,
  "subsample": 0.8,
  "colsample_bytree": 0.8,
  "reg_alpha": 0.1,
  "reg_lambda": 5.0
}
```

### Decision policy

The service does not ship the raw 0.50 cut. Calibrated scores are mapped to three outcomes:

| Decision              | Score range                 |
| --------------------- | --------------------------- |
| `APPROVE`             | `score < 0.016541`          |
| `APPROVE_WITH_REVIEW` | `0.016541 ≤ score < 0.592932` |
| `DECLINE`             | `score ≥ 0.592932`          |

Behaviour on the held-out test set:

| Decision              | Transactions | % of traffic | Fraud caught | Fraud rate within decision |
| --------------------- | ------------ | ------------ | ------------ | -------------------------- |
| `APPROVE`             | 14,321       | 88.5%        | 59           | 0.4%                       |
| `APPROVE_WITH_REVIEW` | 1,577        | 9.7%         | 222          | 14.1%                      |
| `DECLINE`             | 292          | 1.8%         | 253          | 86.6%                      |

This is why the three-tier policy exists. A single hard cut recovers 59% of fraud; routing the uncertain band to human review instead of auto-approving it brings **475 of 534 frauds (89%) in front of either an automatic decline or an analyst**, and leaves only 59 frauds (11%) silently approved. The cost is that analysts review ~9.7% of traffic, and 86% of what lands in the review queue is legitimate — that review-volume-versus-recall trade is the main tuning lever for the thresholds.

### Artefacts

```text
ml/artefacts/version2/
├── fraud_model_tuned.pkl        -> calibrated LightGBM classifier
├── feature_schema_tuned.json    -> authoritative feature order + decision thresholds
├── tuning_results_v2.csv        -> full randomised-search results
└── best_params_v2.json          -> selected hyperparameters
```

`feature_schema_tuned.json` is the contract between training and serving: `src/services/realtime_feature_builder.py` builds its feature vector in exactly the order recorded there.

---

## 2. Earlier iteration — dataset v1 (superseded)

The first modelling round trained a Random Forest and an untuned LightGBM on a smaller synthetic dataset (40,762 train / 10,190 test, 34 features).

| Metric          | Random Forest | LightGBM  |
| --------------- | ------------- | --------- |
| Accuracy        | 99.96%        | 99.94%    |
| Fraud precision | 100.00%       | 98.61%    |
| Fraud recall    | 98.60%        | 99.30%    |
| Fraud F1        | 99.30%        | 98.95%    |
| ROC-AUC         | 0.9999986     | 0.9999940 |
| PR-AUC          | 0.9999510     | 0.9997938 |
| False positives | 0             | 4         |
| Missed frauds   | 4             | 2         |

A calibrated LightGBM on the same data scored PR-AUC 0.99998 with a 2-error confusion matrix.

> **These figures should not be quoted as FraudPulse's performance.** Near-perfect scores on all three models indicate that the v1 synthetic dataset was trivially separable, not that fraud detection was solved. The v2 dataset was rebuilt to be harder and more realistic, and performance fell to PR-AUC 0.72 — that is the honest benchmark, and it is the model that is deployed. The v1 numbers are kept here as a record of the iteration.

### Feature importance

Both v1 models converged on similar signals:

| Rank | Random Forest                  | LightGBM                         |
| ---- | ------------------------------ | -------------------------------- |
| 1    | `seconds_since_last_txn`       | `enriched_amount_usd`            |
| 2    | `cross_border`                 | `seconds_since_last_txn`         |
| 3    | `txn_count_1h`                 | `transaction_country_fraud_rate` |
| 4    | `enriched_amount_usd`          | `authentication_enc`             |
| 5    | `authentication_enc`           | `cross_border`                   |

Transaction amount, timing/velocity, geography, and authentication method carry the signal in both — consistent with the SHAP contributions returned by `POST /api/v1/transactions?explain=true`.
