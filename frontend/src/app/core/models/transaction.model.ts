// Stale legacy decision labels — kept only because the mock-driven Transaction
// Monitor still consumes them. Do NOT use for any live-backend integration.
export type Decision = 'ALLOW' | 'REVIEW' | 'BLOCK';

// Real labels returned by POST /api/v1/transactions (see
// backend/src/services/decision_service.py).
export type BackendDecision = 'APPROVE' | 'APPROVE_WITH_REVIEW' | 'DECLINE';

export type LifecycleStatus = 'AUTHORIZED' | 'SETTLED';

export interface ReasonCode {
  feature: string;
  direction: 'HIGH' | 'LOW';
  contribution: number;
}

// Per-feature SHAP contribution returned when POST /transactions?explain=true.
// Mirrors backend src/schemas/scoring_schemas.FeatureContribution.
export interface FeatureContribution {
  feature: string;
  value: number;
  shap_value: number;
}

// Mirrors backend TransactionDecisionResponse.
export interface ScoreResult {
  transaction_id: string;
  decision: BackendDecision;
  score: number | null;
  model_name?: string | null;
  reason?: string | null;
  contributions?: FeatureContribution[] | null;
}

// Demo-only payload for the Model Demo page. Mirrors the POST
// /api/v1/transactions body PLUS the held-out is_fraud label, which is
// DISPLAY ONLY and must never be sent back to the scoring API.
export interface DemoTransaction {
  transaction_id: string; // raw-CSV id; the DB mints a new one on POST
  card_id: string;
  merchant_id: string;
  timestamp: string;
  enriched_amount_usd: number;
  issuing_bank_country: string;
  transaction_country: string;
  cvv2_result: string;
  avs_result: string;
  pan_entry_mode: string;
  authentication: string;
  card_type: string;
  channel: string;
  transaction_type: string;
  merchant_category_code: string;
  transaction_amount: number | null;
  transaction_currency: string | null;
  transaction_city: string | null;
  terminal_id: string | null;
  is_fraud: 0 | 1; // ground truth — display/comparison only
}

export interface TransactionFeatures {
  enriched_amount_usd: number;
  hour_sin: number;
  hour_cos: number;
  dow_sin: number;
  dow_cos: number;
  is_weekend: boolean;
  is_night: boolean;
  cross_border: boolean;
  card_txn_count_prior: number;
  card_avg_amount_usd_prior: number;
  card_std_amount_usd_prior: number;
  amount_vs_card_avg: number;
  amount_zscore: number;
  seconds_since_last_txn: number;
  txn_count_1h: number;
  txn_count_24h: number;
  high_amount_relative: boolean;
  cross_border_high_amount: boolean;
  velocity_spike_1h: boolean;
  weak_auth_high_value: boolean;
  cvv2_result_enc: number;
  avs_result_enc: number;
  pan_entry_mode_enc: number;
  authentication_enc: number;
  card_type_Credit: number;
  card_type_Debit: number;
  card_type_Prepaid: number;
  channel_ATM: number;
  channel_ECOMMERCE: number;
  channel_POS: number;
  transaction_type_purchase: number;
  transaction_type_withdrawal: number;
  merchant_category_code_fraud_rate: number;
  transaction_country_fraud_rate: number;
}

export interface Transaction {
  id: string;
  userId: string;
  amount: number;
  currency: string;
  merchant: string;
  ts: string;
  userIp?: string;
  decision: Decision;
  score: number;
  modelVersion: string;
  lifecycleStatus: LifecycleStatus;
  reasons: ReasonCode[];
  features: TransactionFeatures;
  isSimulated: boolean;
  isManual: boolean;
  caseId?: string;
  // Persisted columns added in the 2026-05-31 schema alignment. Optional
  // here because the mock store does not populate them yet.
  transaction_type?: string;
  transaction_country?: string;
  is_fraud?: 0 | 1 | null;
}
