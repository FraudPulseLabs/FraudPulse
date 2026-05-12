import { signal } from '@angular/core';
import type { ReasonCode, Transaction } from '../models';

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

const tx = (
  n: number,
  decision: Transaction['decision'],
  score: number,
  amount: number,
  lifecycleStatus: Transaction['lifecycleStatus'],
  reasonList: ReasonCode[] = [],
  caseId?: string,
): Transaction => ({
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
  isSimulated: true,
  isManual: false,
  ...(caseId ? { caseId } : {}),
});

export const MOCK_TRANSACTIONS: readonly Transaction[] = [
  tx(1, 'ALLOW', 0.03, 150, 'SETTLED'),
  tx(2, 'ALLOW', 0.06, 490, 'SETTLED'),
  tx(3, 'ALLOW', 0.08, 850, 'SETTLED'),
  tx(4, 'ALLOW', 0.11, 1250, 'SETTLED'),
  tx(5, 'ALLOW', 0.13, 2200, 'SETTLED'),
  tx(6, 'ALLOW', 0.15, 3150, 'SETTLED'),
  tx(7, 'ALLOW', 0.16, 4300, 'SETTLED'),
  tx(8, 'ALLOW', 0.18, 5200, 'AUTHORIZED', reasons(['known_device', 'LOW', 0.12]), 'CASE-001'),
  tx(9, 'ALLOW', 0.2, 6400, 'SETTLED'),
  tx(10, 'ALLOW', 0.21, 7800, 'SETTLED'),
  tx(11, 'ALLOW', 0.23, 9100, 'SETTLED'),
  tx(12, 'ALLOW', 0.24, 10300, 'SETTLED'),
  tx(13, 'ALLOW', 0.25, 11800, 'SETTLED'),
  tx(14, 'ALLOW', 0.26, 12900, 'SETTLED'),
  tx(15, 'ALLOW', 0.28, 14200, 'AUTHORIZED', reasons(['merchant_history', 'LOW', 0.1]), 'CASE-002'),
  tx(16, 'ALLOW', 0.29, 15500, 'SETTLED'),
  tx(17, 'ALLOW', 0.3, 16800, 'SETTLED'),
  tx(18, 'ALLOW', 0.31, 18200, 'SETTLED'),
  tx(19, 'ALLOW', 0.32, 19400, 'SETTLED'),
  tx(20, 'ALLOW', 0.33, 20600, 'SETTLED'),
  tx(21, 'ALLOW', 0.34, 21900, 'SETTLED'),
  tx(22, 'ALLOW', 0.35, 23100, 'AUTHORIZED', reasons(['amount_percentile', 'HIGH', 0.18]), 'CASE-003'),
  tx(23, 'ALLOW', 0.36, 24400, 'SETTLED'),
  tx(24, 'ALLOW', 0.38, 25800, 'SETTLED'),
  tx(25, 'REVIEW', 0.41, 27100, 'AUTHORIZED', reasons(['amount_zscore', 'HIGH', 0.42], ['new_device', 'HIGH', 0.31], ['merchant_risk', 'LOW', 0.18])),
  tx(26, 'REVIEW', 0.46, 28600, 'AUTHORIZED', reasons(['velocity_1h', 'HIGH', 0.45], ['ip_distance', 'HIGH', 0.28], ['prior_declines', 'LOW', 0.2])),
  tx(27, 'REVIEW', 0.5, 30200, 'AUTHORIZED', reasons(['merchant_risk', 'HIGH', 0.4], ['new_device', 'HIGH', 0.33], ['amount_percentile', 'LOW', 0.2])),
  tx(28, 'REVIEW', 0.55, 31800, 'AUTHORIZED', reasons(['velocity_24h', 'HIGH', 0.47], ['user_history', 'LOW', 0.22], ['ip_reputation', 'HIGH', 0.21])),
  tx(29, 'REVIEW', 0.6, 33600, 'AUTHORIZED', reasons(['amount_zscore', 'HIGH', 0.49], ['device_age', 'LOW', 0.27], ['merchant_country', 'HIGH', 0.2]), 'CASE-004'),
  tx(30, 'REVIEW', 0.64, 35500, 'SETTLED', reasons(['duplicate_pattern', 'HIGH', 0.38], ['new_device', 'HIGH', 0.29], ['merchant_risk', 'LOW', 0.19])),
  tx(31, 'REVIEW', 0.68, 38200, 'AUTHORIZED', reasons(['velocity_1h', 'HIGH', 0.5], ['ip_distance', 'HIGH', 0.25], ['amount_percentile', 'HIGH', 0.2])),
  tx(32, 'REVIEW', 0.71, 40500, 'AUTHORIZED', reasons(['merchant_country', 'HIGH', 0.44], ['user_history', 'LOW', 0.3], ['prior_declines', 'HIGH', 0.18])),
  tx(33, 'REVIEW', 0.74, 43800, 'AUTHORIZED', reasons(['amount_zscore', 'HIGH', 0.52], ['device_age', 'HIGH', 0.24], ['merchant_risk', 'LOW', 0.17])),
  tx(34, 'REVIEW', 0.78, 46200, 'AUTHORIZED', reasons(['velocity_24h', 'HIGH', 0.55], ['ip_reputation', 'HIGH', 0.22], ['user_history', 'LOW', 0.18])),
  tx(35, 'BLOCK', 0.82, 51000, 'AUTHORIZED', reasons(['block_rule', 'HIGH', 0.6], ['amount_zscore', 'HIGH', 0.42], ['new_device', 'HIGH', 0.31], ['merchant_risk', 'HIGH', 0.2])),
  tx(36, 'BLOCK', 0.86, 58500, 'AUTHORIZED', reasons(['velocity_1h', 'HIGH', 0.62], ['ip_reputation', 'HIGH', 0.39], ['prior_declines', 'HIGH', 0.25], ['user_history', 'LOW', 0.18])),
  tx(37, 'BLOCK', 0.89, 64000, 'AUTHORIZED', reasons(['amount_zscore', 'HIGH', 0.65], ['merchant_country', 'HIGH', 0.36], ['new_device', 'HIGH', 0.28], ['device_age', 'LOW', 0.17])),
  tx(38, 'BLOCK', 0.92, 71000, 'AUTHORIZED', reasons(['block_rule', 'HIGH', 0.68], ['duplicate_pattern', 'HIGH', 0.34], ['velocity_24h', 'HIGH', 0.27], ['merchant_risk', 'HIGH', 0.22])),
  tx(39, 'BLOCK', 0.95, 79000, 'AUTHORIZED', reasons(['ip_reputation', 'HIGH', 0.7], ['amount_percentile', 'HIGH', 0.44], ['new_device', 'HIGH', 0.3], ['prior_declines', 'HIGH', 0.25])),
  tx(40, 'BLOCK', 0.97, 85000, 'AUTHORIZED', reasons(['block_rule', 'HIGH', 0.75], ['velocity_1h', 'HIGH', 0.48], ['merchant_country', 'HIGH', 0.32], ['device_age', 'LOW', 0.19])),
];

export const txStore = signal<Transaction[]>([...MOCK_TRANSACTIONS]);
