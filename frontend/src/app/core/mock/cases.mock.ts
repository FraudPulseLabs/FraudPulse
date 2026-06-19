// src/app/core/mock/cases.mock.ts
// Mock data matching the backend CaseRead schema.
// Notes are fetched separately via GET /cases/{id}/notes.
import { signal } from '@angular/core';
import type { FraudCase } from '../models';

const base = Date.parse('2026-04-29T00:00:00Z');
const iso = (daysAgo: number, hoursAgo = 0): string =>
  new Date(base - daysAgo * 86_400_000 - hoursAgo * 3_600_000).toISOString();

export const MOCK_CASES: readonly FraudCase[] = [
  {
    id: 'CASE-001',
    transactionId: 'TX-035',
    title: 'High-value ATM withdrawal - USR-007',
    status: 'OPEN',
    riskLevel: 'HIGH',
    assignedTo: 'analyst@fraudpulse.demo',
    createdAt: iso(1),
    updatedAt: iso(0, 2),
  },
  {
    id: 'CASE-002',
    transactionId: 'TX-038',
    title: 'Velocity anomaly - USR-003 (5 tx in 1h)',
    status: 'OPEN',
    riskLevel: 'HIGH',
    createdAt: iso(2),
    updatedAt: iso(1, 4),
  },
  {
    id: 'CASE-003',
    transactionId: 'TX-039',
    title: 'Suspected account takeover - USR-011',
    status: 'OPEN',
    riskLevel: 'HIGH',
    createdAt: iso(3),
    updatedAt: iso(2, 6),
  },
  {
    id: 'CASE-004',
    transactionId: 'TX-029',
    title: 'Cross-border merchant anomaly - USR-005',
    status: 'INVESTIGATING',
    riskLevel: 'MEDIUM',
    assignedTo: 'lead@fraudpulse.demo',
    createdAt: iso(4),
    updatedAt: iso(3, 10),
  },
  {
    id: 'CASE-005',
    transactionId: 'TX-025',
    title: 'Repeated new-device attempts - USR-009',
    status: 'INVESTIGATING',
    riskLevel: 'HIGH',
    createdAt: iso(5),
    updatedAt: iso(4, 9),
  },
  {
    id: 'CASE-006',
    transactionId: 'TX-030',
    title: 'Duplicate transaction review - USR-006',
    status: 'INVESTIGATING',
    riskLevel: 'MEDIUM',
    createdAt: iso(6),
    updatedAt: iso(5, 10),
  },
  {
    id: 'CASE-007',
    transactionId: 'TX-037',
    title: 'Confirmed fraud - Unknown Merchant TZ',
    status: 'CLOSED',
    riskLevel: 'HIGH',
    resolutionCode: 'CONFIRMED_FRAUD',
    createdAt: iso(7),
    updatedAt: iso(5, 2),
  },
  {
    id: 'CASE-008',
    transactionId: 'TX-034',
    title: 'False positive - known merchant review',
    status: 'CLOSED',
    riskLevel: 'LOW',
    resolutionCode: 'FALSE_POSITIVE',
    createdAt: iso(8),
    updatedAt: iso(6, 2),
  },
];

export const caseStore = signal<FraudCase[]>([...MOCK_CASES]);