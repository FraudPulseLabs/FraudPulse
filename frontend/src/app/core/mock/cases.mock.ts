import { signal } from '@angular/core';
import type { FraudCase } from '../models';

const base = Date.parse('2026-04-29T00:00:00Z');
const iso = (daysAgo: number, hoursAgo = 0): string =>
  new Date(base - daysAgo * 86_400_000 - hoursAgo * 3_600_000).toISOString();

const notes = (count: number) =>
  Array.from({ length: count }, (_, i) => ({
    author: i % 2 === 0 ? 'analyst@fraudpulse.demo' : 'lead@fraudpulse.demo',
    timestamp: iso(i + 1, i * 2),
    body: [
      'Initial review completed and customer profile checked.',
      'Merchant history and transaction velocity require follow up.',
      'Customer contact attempt logged for verification.',
      'Evidence packet updated with linked alert details.',
      'Final review note added for closure.',
    ][i],
  }));

export const MOCK_CASES: readonly FraudCase[] = [
  {
    id: 'CASE-001',
    title: 'High-value ATM withdrawal - USR-007',
    status: 'OPEN',
    riskLevel: 'HIGH',
    linkedAlertIds: ['ALERT-001', 'ALERT-002'],
    linkedTransactionIds: ['TX-008', 'TX-035', 'TX-036'],
    assignedTo: 'analyst@fraudpulse.demo',
    notes: notes(2),
    timeline: [
      { type: 'ALERT_ADDED', timestamp: iso(1, 1), description: 'Two high severity alerts linked', actor: 'system' },
      { type: 'RULE_TRIGGER', timestamp: iso(1, 2), description: 'Block threshold rule triggered', actor: 'rules-engine' },
      { type: 'ASSIGNMENT_CHANGED', timestamp: iso(1, 3), description: 'Assigned to fraud analyst', actor: 'lead@fraudpulse.demo' },
    ],
    createdAt: iso(1),
    updatedAt: iso(0, 2),
  },
  {
    id: 'CASE-002',
    title: 'Velocity anomaly - USR-003 (5 tx in 1h)',
    status: 'OPEN',
    riskLevel: 'HIGH',
    linkedAlertIds: ['ALERT-007', 'ALERT-008'],
    linkedTransactionIds: ['TX-015', 'TX-038', 'TX-028'],
    notes: notes(2),
    timeline: [
      { type: 'ALERT_ADDED', timestamp: iso(2, 1), description: 'Velocity alerts linked', actor: 'system' },
      { type: 'STATUS_CHANGED', timestamp: iso(2, 3), description: 'Case opened', actor: 'analyst@fraudpulse.demo' },
      { type: 'NOTE_ADDED', timestamp: iso(1, 4), description: 'Analyst note added', actor: 'analyst@fraudpulse.demo' },
    ],
    createdAt: iso(2),
    updatedAt: iso(1, 4),
  },
  {
    id: 'CASE-003',
    title: 'Suspected account takeover - USR-011',
    status: 'OPEN',
    riskLevel: 'HIGH',
    linkedAlertIds: ['ALERT-009', 'ALERT-011'],
    linkedTransactionIds: ['TX-022', 'TX-039', 'TX-040'],
    notes: notes(2),
    timeline: [
      { type: 'ALERT_ADDED', timestamp: iso(3, 1), description: 'High score alerts linked', actor: 'system' },
      { type: 'RULE_TRIGGER', timestamp: iso(3, 2), description: 'Device age rule triggered', actor: 'rules-engine' },
      { type: 'NOTE_ADDED', timestamp: iso(2, 6), description: 'Contact attempt logged', actor: 'analyst@fraudpulse.demo' },
    ],
    createdAt: iso(3),
    updatedAt: iso(2, 6),
  },
  {
    id: 'CASE-004',
    title: 'Cross-border merchant anomaly - USR-005',
    status: 'INVESTIGATING',
    riskLevel: 'MEDIUM',
    linkedAlertIds: ['ALERT-010', 'ALERT-013'],
    linkedTransactionIds: ['TX-029', 'TX-031'],
    assignedTo: 'lead@fraudpulse.demo',
    notes: notes(3),
    timeline: [
      { type: 'ALERT_ADDED', timestamp: iso(4, 1), description: 'Merchant country alert linked', actor: 'system' },
      { type: 'STATUS_CHANGED', timestamp: iso(4, 4), description: 'Status changed to INVESTIGATING', actor: 'analyst@fraudpulse.demo' },
      { type: 'ASSIGNMENT_CHANGED', timestamp: iso(3, 8), description: 'Assigned to lead analyst', actor: 'lead@fraudpulse.demo' },
      { type: 'NOTE_ADDED', timestamp: iso(3, 10), description: 'Merchant review note added', actor: 'lead@fraudpulse.demo' },
    ],
    createdAt: iso(4),
    updatedAt: iso(3, 10),
  },
  {
    id: 'CASE-005',
    title: 'Repeated new-device attempts - USR-009',
    status: 'INVESTIGATING',
    riskLevel: 'HIGH',
    linkedAlertIds: ['ALERT-003', 'ALERT-004', 'ALERT-014'],
    linkedTransactionIds: ['TX-025', 'TX-026', 'TX-032'],
    notes: notes(4),
    timeline: [
      { type: 'ALERT_ADDED', timestamp: iso(5, 1), description: 'Three alerts grouped', actor: 'system' },
      { type: 'RULE_TRIGGER', timestamp: iso(5, 2), description: 'New device rule triggered', actor: 'rules-engine' },
      { type: 'STATUS_CHANGED', timestamp: iso(4, 7), description: 'Status changed to INVESTIGATING', actor: 'analyst@fraudpulse.demo' },
      { type: 'NOTE_ADDED', timestamp: iso(4, 9), description: 'Customer verification pending', actor: 'analyst@fraudpulse.demo' },
    ],
    createdAt: iso(5),
    updatedAt: iso(4, 9),
  },
  {
    id: 'CASE-006',
    title: 'Duplicate transaction review - USR-006',
    status: 'INVESTIGATING',
    riskLevel: 'MEDIUM',
    linkedAlertIds: ['ALERT-012', 'ALERT-015'],
    linkedTransactionIds: ['TX-030', 'TX-033'],
    notes: notes(3),
    timeline: [
      { type: 'ALERT_ADDED', timestamp: iso(6, 1), description: 'Duplicate pattern alerts linked', actor: 'system' },
      { type: 'STATUS_CHANGED', timestamp: iso(5, 7), description: 'Status changed to INVESTIGATING', actor: 'analyst@fraudpulse.demo' },
      { type: 'NOTE_ADDED', timestamp: iso(5, 8), description: 'Merchant matching reviewed', actor: 'analyst@fraudpulse.demo' },
      { type: 'ASSIGNMENT_CHANGED', timestamp: iso(5, 10), description: 'Assigned to queue owner', actor: 'lead@fraudpulse.demo' },
    ],
    createdAt: iso(6),
    updatedAt: iso(5, 10),
  },
  {
    id: 'CASE-007',
    title: 'Confirmed fraud - Unknown Merchant TZ',
    status: 'CLOSED',
    riskLevel: 'HIGH',
    linkedAlertIds: ['ALERT-017', 'ALERT-020'],
    linkedTransactionIds: ['TX-035', 'TX-037'],
    resolutionCode: 'CONFIRMED_FRAUD',
    notes: notes(5),
    timeline: [
      { type: 'ALERT_ADDED', timestamp: iso(7, 1), description: 'Fraud alerts linked', actor: 'system' },
      { type: 'STATUS_CHANGED', timestamp: iso(7, 3), description: 'Status changed to INVESTIGATING', actor: 'analyst@fraudpulse.demo' },
      { type: 'NOTE_ADDED', timestamp: iso(6, 4), description: 'Evidence reviewed', actor: 'analyst@fraudpulse.demo' },
      { type: 'RULE_TRIGGER', timestamp: iso(6, 6), description: 'Blacklist rule confirmed', actor: 'rules-engine' },
      { type: 'STATUS_CHANGED', timestamp: iso(5, 2), description: 'Status changed to CLOSED - CONFIRMED_FRAUD', actor: 'lead@fraudpulse.demo' },
    ],
    createdAt: iso(7),
    updatedAt: iso(5, 2),
  },
  {
    id: 'CASE-008',
    title: 'False positive - known merchant review',
    status: 'CLOSED',
    riskLevel: 'LOW',
    linkedAlertIds: ['ALERT-016', 'ALERT-018', 'ALERT-019'],
    linkedTransactionIds: ['TX-034', 'TX-036', 'TX-025'],
    resolutionCode: 'FALSE_POSITIVE',
    notes: notes(5),
    timeline: [
      { type: 'ALERT_ADDED', timestamp: iso(8, 1), description: 'Resolved alerts linked', actor: 'system' },
      { type: 'STATUS_CHANGED', timestamp: iso(8, 4), description: 'Status changed to INVESTIGATING', actor: 'analyst@fraudpulse.demo' },
      { type: 'NOTE_ADDED', timestamp: iso(7, 5), description: 'Customer confirmation received', actor: 'analyst@fraudpulse.demo' },
      { type: 'ASSIGNMENT_CHANGED', timestamp: iso(7, 8), description: 'Escalated for closure review', actor: 'lead@fraudpulse.demo' },
      { type: 'STATUS_CHANGED', timestamp: iso(6, 2), description: 'Status changed to CLOSED - FALSE_POSITIVE', actor: 'lead@fraudpulse.demo' },
    ],
    createdAt: iso(8),
    updatedAt: iso(6, 2),
  },
];

export const caseStore = signal<FraudCase[]>([...MOCK_CASES]);
