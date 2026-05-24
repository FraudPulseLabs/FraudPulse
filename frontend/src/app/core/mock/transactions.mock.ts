import { signal } from '@angular/core';
import type { ReasonCode, Transaction, TransactionFeatures } from '../models';

const base = Date.parse('2026-04-29T00:00:00Z');
const iso = (daysAgo: number, hoursAgo = 0): string =>
  new Date(base - daysAgo * 86_400_000 - hoursAgo * 3_600_000).toISOString();

const merchants = [
  'Jumia Online',
  'M-PESA Transfer',
  'KCB ATM Withdrawal',
  'Equity Bank ATM',
  'KFC Westlands',
  'Shell Petrol Ngong Rd',
  'Carrefour Westgate',
  'Netflix Inc',
  'Airtel Money Transfer',
  'Unknown Merchant TZ',
  'Naivas Supermarket',
  'DStv Subscription',
] as const;

const reasons = (...items: [string, 'HIGH' | 'LOW', number][]): ReasonCode[] =>
  items.map(([feature, direction, contribution]) => ({ feature, direction, contribution }));

const round = (value: number, digits = 2): number => Number(value.toFixed(digits));

const buildFeatures = (n: number, amount: number): TransactionFeatures => {
  const enrichedAmountUsd = round(amount / 129 + n * 0.41);
  const hour = (n * 3) % 24;
  const dayOfWeek = n % 7;
  const isWeekend = dayOfWeek === 0 || dayOfWeek === 6;
  const isNight = hour < 6 || hour >= 22;
  const crossBorder = n % 4 === 0 || n % 9 === 0;
  const cardTxnCountPrior = 3 + (n * 2) % 48;
  const cardAvgAmountUsdPrior = round(35 + n * 2.8, 2);
  const cardStdAmountUsdPrior = round(8 + (n % 9) * 3.4, 2);
  const amountVsCardAvg = round(enrichedAmountUsd / cardAvgAmountUsdPrior, 3);
  const amountZscore = round((enrichedAmountUsd - cardAvgAmountUsdPrior) / Math.max(cardStdAmountUsdPrior, 1), 3);
  const secondsSinceLastTxn = 35 + (n * 173) % 86_400;
  const txnCount1h = 1 + (n % 8);
  const txnCount24h = 4 + (n * 3) % 36;
  const highAmountRelative = amountVsCardAvg >= 1.75;
  const crossBorderHighAmount = crossBorder && highAmountRelative;
  const velocitySpike1h = txnCount1h >= 6;
  const authenticationEnc = n % 3;
  const weakAuthHighValue = authenticationEnc === 0 && enrichedAmountUsd >= 240;
  const cardType = n % 3;
  const channel = n % 3;
  const isWithdrawal = n % 5 === 0 || channel === 0;

  return {
    enriched_amount_usd: enrichedAmountUsd,
    hour_sin: round(Math.sin((2 * Math.PI * hour) / 24), 4),
    hour_cos: round(Math.cos((2 * Math.PI * hour) / 24), 4),
    dow_sin: round(Math.sin((2 * Math.PI * dayOfWeek) / 7), 4),
    dow_cos: round(Math.cos((2 * Math.PI * dayOfWeek) / 7), 4),
    is_weekend: isWeekend,
    is_night: isNight,
    cross_border: crossBorder,
    card_txn_count_prior: cardTxnCountPrior,
    card_avg_amount_usd_prior: cardAvgAmountUsdPrior,
    card_std_amount_usd_prior: cardStdAmountUsdPrior,
    amount_vs_card_avg: amountVsCardAvg,
    amount_zscore: amountZscore,
    seconds_since_last_txn: secondsSinceLastTxn,
    txn_count_1h: txnCount1h,
    txn_count_24h: txnCount24h,
    high_amount_relative: highAmountRelative,
    cross_border_high_amount: crossBorderHighAmount,
    velocity_spike_1h: velocitySpike1h,
    weak_auth_high_value: weakAuthHighValue,
    cvv2_result_enc: n % 3,
    avs_result_enc: (n + 1) % 4,
    pan_entry_mode_enc: [1, 2, 5, 7][n % 4],
    authentication_enc: authenticationEnc,
    card_type_Credit: cardType === 0 ? 1 : 0,
    card_type_Debit: cardType === 1 ? 1 : 0,
    card_type_Prepaid: cardType === 2 ? 1 : 0,
    channel_ATM: channel === 0 ? 1 : 0,
    channel_ECOMMERCE: channel === 1 ? 1 : 0,
    channel_POS: channel === 2 ? 1 : 0,
    transaction_type_purchase: isWithdrawal ? 0 : 1,
    transaction_type_withdrawal: isWithdrawal ? 1 : 0,
    merchant_category_code_fraud_rate: round(0.01 + ((n * 7) % 18) / 100, 3),
    transaction_country_fraud_rate: round(0.008 + ((n * 5) % 16) / 100, 3),
  };
};

const tx = (
  n: number,
  decision: Transaction['decision'],
  score: number,
  amount: number,
  lifecycleStatus: Transaction['lifecycleStatus'],
  reasonList: ReasonCode[] = [],
  caseId?: string,
): Transaction => {
  const features = buildFeatures(n, amount);

  return {
    id: `TX-${String(n).padStart(3, '0')}`,
    userId: `USR-${String(((n - 1) % 12) + 1).padStart(3, '0')}`,
    amount,
    currency: 'KES',
    merchant: merchants[(n - 1) % merchants.length],
    ts: iso((n - 1) % 7, n % 24),
    userIp: `102.68.${(n * 7) % 255}.${(n * 13) % 255}`,
    decision,
    score,
    modelVersion: 'v1.0',
    lifecycleStatus,
    reasons: reasonList,
    features,
    isSimulated: true,
    isManual: false,
    ...(caseId ? { caseId } : {}),
  };
};

export const MOCK_TRANSACTIONS: readonly Transaction[] = [
  tx(1, 'ALLOW', 0.03, 150, 'SETTLED'),
  tx(2, 'ALLOW', 0.06, 490, 'SETTLED'),
  tx(3, 'ALLOW', 0.08, 850, 'SETTLED'),
  tx(4, 'ALLOW', 0.11, 1250, 'SETTLED'),
  tx(5, 'ALLOW', 0.13, 2200, 'SETTLED'),
  tx(6, 'ALLOW', 0.15, 3150, 'SETTLED'),
  tx(7, 'ALLOW', 0.16, 4300, 'SETTLED'),
  tx(8, 'ALLOW', 0.18, 5200, 'AUTHORIZED', reasons(['amount_zscore', 'LOW', 0.12]), 'CASE-001'),
  tx(9, 'ALLOW', 0.2, 6400, 'SETTLED'),
  tx(10, 'ALLOW', 0.21, 7800, 'SETTLED'),
  tx(11, 'ALLOW', 0.23, 9100, 'SETTLED'),
  tx(12, 'ALLOW', 0.24, 10300, 'SETTLED'),
  tx(13, 'ALLOW', 0.25, 11800, 'SETTLED'),
  tx(14, 'ALLOW', 0.26, 12900, 'SETTLED'),
  tx(15, 'ALLOW', 0.28, 14200, 'AUTHORIZED', reasons(['merchant_category_code_fraud_rate', 'LOW', 0.1]), 'CASE-002'),
  tx(16, 'ALLOW', 0.29, 15500, 'SETTLED'),
  tx(17, 'ALLOW', 0.3, 16800, 'SETTLED'),
  tx(18, 'ALLOW', 0.31, 18200, 'SETTLED'),
  tx(19, 'ALLOW', 0.32, 19400, 'SETTLED'),
  tx(20, 'ALLOW', 0.33, 20600, 'SETTLED'),
  tx(21, 'ALLOW', 0.34, 21900, 'SETTLED'),
  tx(22, 'ALLOW', 0.35, 23100, 'AUTHORIZED', reasons(['amount_vs_card_avg', 'HIGH', 0.18]), 'CASE-003'),
  tx(23, 'ALLOW', 0.36, 24400, 'SETTLED'),
  tx(24, 'ALLOW', 0.38, 25800, 'SETTLED'),
  tx(25, 'REVIEW', 0.41, 27100, 'AUTHORIZED', reasons(['amount_zscore', 'HIGH', 0.42], ['weak_auth_high_value', 'HIGH', 0.31], ['merchant_category_code_fraud_rate', 'LOW', 0.18])),
  tx(26, 'REVIEW', 0.46, 28600, 'AUTHORIZED', reasons(['velocity_spike_1h', 'HIGH', 0.45], ['cross_border', 'HIGH', 0.28], ['card_std_amount_usd_prior', 'LOW', 0.2])),
  tx(27, 'REVIEW', 0.5, 30200, 'AUTHORIZED', reasons(['merchant_category_code_fraud_rate', 'HIGH', 0.4], ['cross_border_high_amount', 'HIGH', 0.33], ['amount_vs_card_avg', 'LOW', 0.2])),
  tx(28, 'REVIEW', 0.55, 31800, 'AUTHORIZED', reasons(['txn_count_24h', 'HIGH', 0.47], ['card_txn_count_prior', 'LOW', 0.22], ['transaction_country_fraud_rate', 'HIGH', 0.21])),
  tx(29, 'REVIEW', 0.6, 33600, 'AUTHORIZED', reasons(['amount_zscore', 'HIGH', 0.49], ['authentication_enc', 'LOW', 0.27], ['cross_border', 'HIGH', 0.2]), 'CASE-004'),
  tx(30, 'REVIEW', 0.64, 35500, 'SETTLED', reasons(['cross_border_high_amount', 'HIGH', 0.38], ['weak_auth_high_value', 'HIGH', 0.29], ['merchant_category_code_fraud_rate', 'LOW', 0.19])),
  tx(31, 'REVIEW', 0.68, 38200, 'AUTHORIZED', reasons(['velocity_spike_1h', 'HIGH', 0.5], ['seconds_since_last_txn', 'HIGH', 0.25], ['amount_vs_card_avg', 'HIGH', 0.2])),
  tx(32, 'REVIEW', 0.71, 40500, 'AUTHORIZED', reasons(['transaction_country_fraud_rate', 'HIGH', 0.44], ['card_txn_count_prior', 'LOW', 0.3], ['weak_auth_high_value', 'HIGH', 0.18])),
  tx(33, 'REVIEW', 0.74, 43800, 'AUTHORIZED', reasons(['amount_zscore', 'HIGH', 0.52], ['is_night', 'HIGH', 0.24], ['merchant_category_code_fraud_rate', 'LOW', 0.17])),
  tx(34, 'REVIEW', 0.78, 46200, 'AUTHORIZED', reasons(['txn_count_24h', 'HIGH', 0.55], ['transaction_country_fraud_rate', 'HIGH', 0.22], ['card_txn_count_prior', 'LOW', 0.18])),
  tx(35, 'BLOCK', 0.82, 51000, 'AUTHORIZED', reasons(['cross_border_high_amount', 'HIGH', 0.6], ['amount_zscore', 'HIGH', 0.42], ['weak_auth_high_value', 'HIGH', 0.31], ['merchant_category_code_fraud_rate', 'HIGH', 0.2])),
  tx(36, 'BLOCK', 0.86, 58500, 'AUTHORIZED', reasons(['velocity_spike_1h', 'HIGH', 0.62], ['transaction_country_fraud_rate', 'HIGH', 0.39], ['txn_count_1h', 'HIGH', 0.25], ['card_txn_count_prior', 'LOW', 0.18])),
  tx(37, 'BLOCK', 0.89, 64000, 'AUTHORIZED', reasons(['amount_zscore', 'HIGH', 0.65], ['cross_border', 'HIGH', 0.36], ['weak_auth_high_value', 'HIGH', 0.28], ['authentication_enc', 'LOW', 0.17])),
  tx(38, 'BLOCK', 0.92, 71000, 'AUTHORIZED', reasons(['cross_border_high_amount', 'HIGH', 0.68], ['velocity_spike_1h', 'HIGH', 0.34], ['txn_count_24h', 'HIGH', 0.27], ['merchant_category_code_fraud_rate', 'HIGH', 0.22])),
  tx(39, 'BLOCK', 0.95, 79000, 'AUTHORIZED', reasons(['transaction_country_fraud_rate', 'HIGH', 0.7], ['amount_vs_card_avg', 'HIGH', 0.44], ['weak_auth_high_value', 'HIGH', 0.3], ['txn_count_1h', 'HIGH', 0.25])),
  tx(40, 'BLOCK', 0.97, 85000, 'AUTHORIZED', reasons(['cross_border_high_amount', 'HIGH', 0.75], ['velocity_spike_1h', 'HIGH', 0.48], ['cross_border', 'HIGH', 0.32], ['authentication_enc', 'LOW', 0.19])),
];

export const txStore = signal<Transaction[]>([...MOCK_TRANSACTIONS]);
