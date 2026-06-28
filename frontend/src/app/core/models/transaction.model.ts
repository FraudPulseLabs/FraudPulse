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

/** Raw row from `GET /api/v1/transactions` (snake_case). */
export interface TransactionApiRead {
  id: string;
  transaction_amount: number;
  transaction_currency: string;
  merchant_id: string;
  ts: string;
  user_ip?: string | null;
  decision?: BackendDecision | string | null;
  lifecycle_status: LifecycleStatus;
  is_simulated: boolean;
  is_manually_created: boolean;
  card_id?: string | null;
  score?: number | null;
  model_version?: string | null;
  transaction_type?: string | null;
  transaction_country?: string | null;
  is_fraud?: boolean | null;
}

/** Raw row from `GET /api/v1/transactions/:id` (includes detail fields). */
export interface TransactionDetailApiRead extends TransactionApiRead {
  reasons?: ReasonCodeApiRead[];
  features?: Partial<TransactionFeatures> | null;
}

export interface ReasonCodeApiRead {
  feature: string;
  direction: 'HIGH' | 'LOW';
  contribution: number;
}

export function mapBackendDecisionToUi(
  decision: BackendDecision | string | null | undefined,
): Decision {
  switch (decision) {
    case 'APPROVE':
      return 'ALLOW';
    case 'APPROVE_WITH_REVIEW':
      return 'REVIEW';
    case 'DECLINE':
      return 'BLOCK';
    default:
      return 'ALLOW';
  }
}

export function emptyTransactionFeatures(): TransactionFeatures {
  return {
    enriched_amount_usd: 0,
    hour_sin: 0,
    hour_cos: 0,
    dow_sin: 0,
    dow_cos: 0,
    is_weekend: false,
    is_night: false,
    cross_border: false,
    card_txn_count_prior: 0,
    card_avg_amount_usd_prior: 0,
    card_std_amount_usd_prior: 0,
    amount_vs_card_avg: 0,
    amount_zscore: 0,
    seconds_since_last_txn: 0,
    txn_count_1h: 0,
    txn_count_24h: 0,
    high_amount_relative: false,
    cross_border_high_amount: false,
    velocity_spike_1h: false,
    weak_auth_high_value: false,
    cvv2_result_enc: 0,
    avs_result_enc: 0,
    pan_entry_mode_enc: 0,
    authentication_enc: 0,
    card_type_Credit: 0,
    card_type_Debit: 0,
    card_type_Prepaid: 0,
    channel_ATM: 0,
    channel_ECOMMERCE: 0,
    channel_POS: 0,
    transaction_type_purchase: 0,
    transaction_type_withdrawal: 0,
    merchant_category_code_fraud_rate: 0,
    transaction_country_fraud_rate: 0,
  };
}

function mapFeaturesFromApi(raw: Partial<TransactionFeatures> | null | undefined): TransactionFeatures {
  const features = emptyTransactionFeatures();
  if (!raw) return features;

  for (const key of Object.keys(features) as (keyof TransactionFeatures)[]) {
    const value = raw[key];
    if (value !== undefined && value !== null) {
      features[key] = value as never;
    }
  }
  return features;
}

function mapReasonsFromApi(reasons: ReasonCodeApiRead[] | null | undefined): ReasonCode[] {
  return (reasons ?? []).map((reason) => ({
    feature: reason.feature,
    direction: reason.direction,
    contribution: Number(reason.contribution),
  }));
}

function fallbackScore(
  score: number | null | undefined,
  decision: BackendDecision | string | null | undefined,
): number {
  if (score != null) return Number(score);
  if (decision === 'DECLINE') return 0.95;
  if (decision === 'APPROVE_WITH_REVIEW') return 0.5;
  return 0;
}

export function mapTransactionFromApi(row: TransactionApiRead): Transaction {
  return {
    id: row.id,
    userId: row.card_id ?? 'unknown',
    amount: Number(row.transaction_amount),
    currency: row.transaction_currency,
    merchant: row.merchant_id,
    ts: row.ts,
    userIp: row.user_ip ?? undefined,
    decision: mapBackendDecisionToUi(row.decision),
    score: fallbackScore(row.score, row.decision),
    modelVersion: row.model_version ?? 'unknown',
    lifecycleStatus: row.lifecycle_status,
    reasons: [],
    features: emptyTransactionFeatures(),
    isSimulated: row.is_simulated,
    isManual: row.is_manually_created,
    transaction_type: row.transaction_type ?? undefined,
    transaction_country: row.transaction_country ?? undefined,
    is_fraud:
      row.is_fraud == null ? undefined : row.is_fraud ? 1 : 0,
  };
}

export function mapTransactionDetailFromApi(row: TransactionDetailApiRead): Transaction {
  return {
    ...mapTransactionFromApi(row),
    reasons: mapReasonsFromApi(row.reasons),
    features: mapFeaturesFromApi(row.features),
  };
}
