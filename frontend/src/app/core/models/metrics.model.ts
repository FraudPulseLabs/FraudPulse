export interface DecisionBucket {
  count: number;
  pct: number;
}

export interface MetricsSummary {
  transactionVolume: { lastHour: number; lastDay: number };
  scoreDistribution: { mean: number; median: number; p95: number };
  decisionSplit: { ALLOW: DecisionBucket; REVIEW: DecisionBucket; BLOCK: DecisionBucket };
  openAlerts: number;
  activeCases: number;
  avgCaseAgeDays: number;
  modelVersion: string;
  systemStatus: 'OK' | 'DEGRADED' | 'DOWN';
  lastUpdated: string;
}
