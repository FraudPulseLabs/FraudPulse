// src/app/core/mock/alerts.mock.ts
import { signal } from '@angular/core';
import type { Alert } from '../models';

const base = Date.parse('2026-04-29T00:00:00Z');
const iso = (hoursAgo: number): string => new Date(base - hoursAgo * 3_600_000).toISOString();

export const MOCK_ALERTS: readonly Alert[] = [
  { id: 'ALERT-001', transactionId: 'TX-035', reason: 'FRAUD_SCORE_DECLINE',      severity: 'HIGH',   createdAt: iso(1)   },
  { id: 'ALERT-002', transactionId: 'TX-036', reason: 'FRAUD_REVIEW_REQUIRED',    severity: 'HIGH',   createdAt: iso(2)   },
  { id: 'ALERT-003', transactionId: 'TX-025', reason: 'FRAUD_REVIEW_REQUIRED',    severity: 'MEDIUM', createdAt: iso(4)   },
  { id: 'ALERT-004', transactionId: 'TX-026', reason: 'FRAUD_SCORE_DECLINE',      severity: 'MEDIUM', createdAt: iso(5)   },
  { id: 'ALERT-005', transactionId: 'TX-037', reason: 'MERCHANT_BLACKLISTED',     severity: 'HIGH',   createdAt: iso(7)   },
  { id: 'ALERT-006', transactionId: 'TX-027', reason: 'FRAUD_REVIEW_REQUIRED',    severity: 'MEDIUM', createdAt: iso(9)   },
  { id: 'ALERT-007', transactionId: 'TX-038', reason: 'FRAUD_SCORE_DECLINE',      severity: 'HIGH',   createdAt: iso(14)  },
  { id: 'ALERT-008', transactionId: 'TX-028', reason: 'FRAUD_REVIEW_REQUIRED',    severity: 'MEDIUM', createdAt: iso(18)  },
  { id: 'ALERT-009', transactionId: 'TX-039', reason: 'FRAUD_SCORE_DECLINE',      severity: 'HIGH',   createdAt: iso(22)  },
  { id: 'ALERT-010', transactionId: 'TX-029', reason: 'MERCHANT_BLACKLISTED',     severity: 'MEDIUM', createdAt: iso(27)  },
  { id: 'ALERT-011', transactionId: 'TX-040', reason: 'FRAUD_SCORE_DECLINE',      severity: 'HIGH',   createdAt: iso(31)  },
  { id: 'ALERT-012', transactionId: 'TX-030', reason: 'FRAUD_SCORE_DECLINE',      severity: 'LOW',    createdAt: iso(36)  },
  { id: 'ALERT-013', transactionId: 'TX-031', reason: 'FRAUD_REVIEW_REQUIRED',    severity: 'MEDIUM', createdAt: iso(42)  },
  { id: 'ALERT-014', transactionId: 'TX-032', reason: 'FRAUD_REVIEW_REQUIRED',    severity: 'MEDIUM', createdAt: iso(49)  },
  { id: 'ALERT-015', transactionId: 'TX-033', reason: 'MERCHANT_BLACKLISTED',     severity: 'LOW',    createdAt: iso(55)  },
  { id: 'ALERT-016', transactionId: 'TX-034', reason: 'FRAUD_REVIEW_REQUIRED',    severity: 'MEDIUM', createdAt: iso(63)  },
  { id: 'ALERT-017', transactionId: 'TX-035', reason: 'FRAUD_SCORE_DECLINE',      severity: 'HIGH',   createdAt: iso(71)  },
  { id: 'ALERT-018', transactionId: 'TX-036', reason: 'FRAUD_SCORE_DECLINE',      severity: 'HIGH',   createdAt: iso(84)  },
  { id: 'ALERT-019', transactionId: 'TX-025', reason: 'FRAUD_REVIEW_REQUIRED',    severity: 'LOW',    createdAt: iso(96)  },
  { id: 'ALERT-020', transactionId: 'TX-037', reason: 'FRAUD_SCORE_DECLINE',      severity: 'HIGH',   createdAt: iso(108) },
];

export const alertStore = signal<Alert[]>([...MOCK_ALERTS]);