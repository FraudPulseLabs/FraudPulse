import type { MetricsSummary } from '../models';

export const MOCK_METRICS: MetricsSummary = {
  transactionVolume: { lastHour: 47, lastDay: 892 },
  scoreDistribution: { mean: 0.28, median: 0.19, p95: 0.83 },
  decisionSplit: {
    ALLOW: { count: 734, pct: 82.3 },
    REVIEW: { count: 118, pct: 13.2 },
    BLOCK: { count: 40, pct: 4.5 },
  },
  openAlerts: 6,
  activeCases: 6,
  avgCaseAgeDays: 3.2,
  modelVersion: 'v1.0',
  systemStatus: 'OK',
  lastUpdated: new Date().toISOString(),
};
