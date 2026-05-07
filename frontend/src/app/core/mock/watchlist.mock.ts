import { signal } from '@angular/core';
import type { WatchlistEntry } from '../models';

const base = Date.parse('2026-04-29T00:00:00Z');
const iso = (days: number): string => new Date(base + days * 86_400_000).toISOString();
const created = (daysAgo: number): string => new Date(base - daysAgo * 86_400_000).toISOString();

export const MOCK_WATCHLIST: readonly WatchlistEntry[] = [
  { id: 'WL-001', entityType: 'USER', entityId: 'USR-007', reason: 'Repeated block decisions', severity: 'HIGH', isBlacklist: true, addedBy: 'analyst@fraudpulse.demo', createdAt: created(1) },
  { id: 'WL-002', entityType: 'USER', entityId: 'USR-003', reason: 'Velocity review', severity: 'MEDIUM', isBlacklist: false, addedBy: 'analyst@fraudpulse.demo', expiresAt: iso(7), createdAt: created(2) },
  { id: 'WL-003', entityType: 'USER', entityId: 'USR-011', reason: 'Account takeover signal', severity: 'HIGH', isBlacklist: false, addedBy: 'lead@fraudpulse.demo', expiresAt: iso(14), createdAt: created(3) },
  { id: 'WL-004', entityType: 'USER', entityId: 'USR-009', reason: 'New device attempts', severity: 'MEDIUM', isBlacklist: false, addedBy: 'analyst@fraudpulse.demo', expiresAt: iso(21), createdAt: created(4) },
  { id: 'WL-005', entityType: 'USER', entityId: 'USR-012', reason: 'Manual analyst review', severity: 'LOW', isBlacklist: false, addedBy: 'lead@fraudpulse.demo', createdAt: created(5) },
  { id: 'WL-006', entityType: 'MERCHANT', entityId: 'Unknown Merchant TZ', reason: 'Confirmed fraud merchant', severity: 'HIGH', isBlacklist: true, addedBy: 'lead@fraudpulse.demo', createdAt: created(1) },
  { id: 'WL-007', entityType: 'MERCHANT', entityId: 'FastCash Mobile', reason: 'High dispute volume', severity: 'HIGH', isBlacklist: false, addedBy: 'analyst@fraudpulse.demo', expiresAt: iso(28), createdAt: created(6) },
  { id: 'WL-008', entityType: 'MERCHANT', entityId: 'QuickLoan KE', reason: 'Manual review merchant', severity: 'MEDIUM', isBlacklist: false, addedBy: 'analyst@fraudpulse.demo', expiresAt: iso(14), createdAt: created(7) },
  { id: 'WL-009', entityType: 'MERCHANT', entityId: 'BetWay Kenya', reason: 'Risk category watch', severity: 'MEDIUM', isBlacklist: false, addedBy: 'lead@fraudpulse.demo', createdAt: created(8) },
  { id: 'WL-010', entityType: 'MERCHANT', entityId: 'OnlineCasino254', reason: 'High chargeback category', severity: 'HIGH', isBlacklist: false, addedBy: 'analyst@fraudpulse.demo', expiresAt: iso(21), createdAt: created(9) },
  { id: 'WL-011', entityType: 'TRANSACTION', entityId: 'TX-035', reason: 'Blocked high-value attempt', severity: 'HIGH', isBlacklist: false, addedBy: 'analyst@fraudpulse.demo', expiresAt: iso(5), createdAt: created(1) },
  { id: 'WL-012', entityType: 'TRANSACTION', entityId: 'TX-036', reason: 'Velocity-linked block', severity: 'HIGH', isBlacklist: false, addedBy: 'analyst@fraudpulse.demo', expiresAt: iso(7), createdAt: created(2) },
  { id: 'WL-013', entityType: 'TRANSACTION', entityId: 'TX-037', reason: 'Country anomaly block', severity: 'HIGH', isBlacklist: false, addedBy: 'lead@fraudpulse.demo', expiresAt: iso(14), createdAt: created(3) },
  { id: 'WL-014', entityType: 'TRANSACTION', entityId: 'TX-038', reason: 'Duplicate pattern block', severity: 'MEDIUM', isBlacklist: false, addedBy: 'analyst@fraudpulse.demo', createdAt: created(4) },
  { id: 'WL-015', entityType: 'TRANSACTION', entityId: 'TX-039', reason: 'IP reputation block', severity: 'HIGH', isBlacklist: false, addedBy: 'lead@fraudpulse.demo', expiresAt: iso(28), createdAt: created(5) },
];

export const watchlistStore = signal<WatchlistEntry[]>([...MOCK_WATCHLIST]);
