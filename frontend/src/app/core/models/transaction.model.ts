export type Decision = 'ALLOW' | 'REVIEW' | 'BLOCK';
export type LifecycleStatus = 'AUTHORIZED' | 'SETTLED';

export interface ReasonCode {
  feature: string;
  direction: 'HIGH' | 'LOW';
  contribution: number;
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
}
