import { signal } from '@angular/core';
import type { Alert } from '../models';

const base = Date.parse('2026-04-29T00:00:00Z');
const iso = (hoursAgo: number): string => new Date(base - hoursAgo * 3_600_000).toISOString();

export const MOCK_ALERTS: readonly Alert[] = [
  { id: 'ALERT-001', transactionId: 'TX-035', reason: 'Score exceeded block threshold', severity: 'HIGH', status: 'NEW', createdAt: iso(1), caseId: 'CASE-001' },
  { id: 'ALERT-002', transactionId: 'TX-036', reason: 'Unusual transaction velocity', severity: 'HIGH', status: 'NEW', createdAt: iso(2), caseId: 'CASE-001' },
  { id: 'ALERT-003', transactionId: 'TX-025', reason: 'Amount anomaly - z-score > 3', severity: 'MEDIUM', status: 'NEW', createdAt: iso(4) },
  { id: 'ALERT-004', transactionId: 'TX-026', reason: 'New device detected', severity: 'MEDIUM', status: 'NEW', createdAt: iso(5) },
  { id: 'ALERT-005', transactionId: 'TX-037', reason: 'Rule: amount > KES 50,000', severity: 'HIGH', status: 'NEW', createdAt: iso(7) },
  { id: 'ALERT-006', transactionId: 'TX-027', reason: 'Flagged user activity', severity: 'MEDIUM', status: 'NEW', createdAt: iso(9) },
  { id: 'ALERT-007', transactionId: 'TX-038', reason: 'Duplicate transaction detected', severity: 'HIGH', status: 'ACKNOWLEDGED', createdAt: iso(14), acknowledgedAt: iso(12), caseId: 'CASE-002' },
  { id: 'ALERT-008', transactionId: 'TX-028', reason: 'Unusual transaction velocity', severity: 'MEDIUM', status: 'ACKNOWLEDGED', createdAt: iso(18), acknowledgedAt: iso(16), caseId: 'CASE-002' },
  { id: 'ALERT-009', transactionId: 'TX-039', reason: 'Score exceeded block threshold', severity: 'HIGH', status: 'ACKNOWLEDGED', createdAt: iso(22), acknowledgedAt: iso(20), caseId: 'CASE-003' },
  { id: 'ALERT-010', transactionId: 'TX-029', reason: 'New device detected', severity: 'MEDIUM', status: 'ACKNOWLEDGED', createdAt: iso(27), acknowledgedAt: iso(24), caseId: 'CASE-004' },
  { id: 'ALERT-011', transactionId: 'TX-040', reason: 'Rule: amount > KES 50,000', severity: 'HIGH', status: 'ACKNOWLEDGED', createdAt: iso(31), acknowledgedAt: iso(29) },
  { id: 'ALERT-012', transactionId: 'TX-030', reason: 'Duplicate transaction detected', severity: 'LOW', status: 'ACKNOWLEDGED', createdAt: iso(36), acknowledgedAt: iso(34) },
  { id: 'ALERT-013', transactionId: 'TX-031', reason: 'Amount anomaly - z-score > 3', severity: 'MEDIUM', status: 'ACKNOWLEDGED', createdAt: iso(42), acknowledgedAt: iso(39) },
  { id: 'ALERT-014', transactionId: 'TX-032', reason: 'Flagged user activity', severity: 'MEDIUM', status: 'ACKNOWLEDGED', createdAt: iso(49), acknowledgedAt: iso(45) },
  { id: 'ALERT-015', transactionId: 'TX-033', reason: 'New device detected', severity: 'LOW', status: 'ACKNOWLEDGED', createdAt: iso(55), acknowledgedAt: iso(51) },
  { id: 'ALERT-016', transactionId: 'TX-034', reason: 'Unusual transaction velocity', severity: 'MEDIUM', status: 'RESOLVED', createdAt: iso(63), acknowledgedAt: iso(60), resolvedAt: iso(48), resolutionNote: 'Verified legitimate' },
  { id: 'ALERT-017', transactionId: 'TX-035', reason: 'Rule: amount > KES 50,000', severity: 'HIGH', status: 'RESOLVED', createdAt: iso(71), acknowledgedAt: iso(68), resolvedAt: iso(50), resolutionNote: 'Confirmed fraud' },
  { id: 'ALERT-018', transactionId: 'TX-036', reason: 'Duplicate transaction detected', severity: 'HIGH', status: 'RESOLVED', createdAt: iso(84), acknowledgedAt: iso(80), resolvedAt: iso(70), resolutionNote: 'False positive - known merchant' },
  { id: 'ALERT-019', transactionId: 'TX-025', reason: 'Amount anomaly - z-score > 3', severity: 'LOW', status: 'RESOLVED', createdAt: iso(96), acknowledgedAt: iso(92), resolvedAt: iso(86), resolutionNote: 'Customer confirmed activity' },
  { id: 'ALERT-020', transactionId: 'TX-037', reason: 'Score exceeded block threshold', severity: 'HIGH', status: 'RESOLVED', createdAt: iso(108), acknowledgedAt: iso(100), resolvedAt: iso(90), resolutionNote: 'Confirmed fraud' },
];

export const alertStore = signal<Alert[]>([...MOCK_ALERTS]);
