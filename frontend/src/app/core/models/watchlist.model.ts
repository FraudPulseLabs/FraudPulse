export type WatchlistEntityType = 'TRANSACTION' | 'USER' | 'MERCHANT';

export interface WatchlistEntry {
  id: string;
  entityType: WatchlistEntityType;
  entityId: string;
  reason: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH';
  isBlacklist: boolean;
  addedBy: string;
  expiresAt?: string;
  createdAt: string;
}
