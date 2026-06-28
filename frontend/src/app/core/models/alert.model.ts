// src/app/core/models/alert.model.ts

export type AlertReason =
  | 'FRAUD_REVIEW_REQUIRED'
  | 'FRAUD_SCORE_DECLINE'
  | 'MERCHANT_BLACKLISTED';

export type AlertSeverity = 'LOW' | 'MEDIUM' | 'HIGH';

export interface Alert {
  id: string;
  transactionId: string;
  reason: AlertReason;
  severity: AlertSeverity;
  createdAt: string; // ISO 8601 timestamp
}