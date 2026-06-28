export type WatchlistEntityType = 'TRANSACTION' | 'USER' | 'MERCHANT';
export type RiskSeverity = 'LOW' | 'MEDIUM' | 'HIGH';

/** Frontend view model (camelCase). */
export interface WatchlistEntry {
  id: string;
  entityType: WatchlistEntityType;
  entityId: string;
  reason: string;
  severity: RiskSeverity;
  isBlacklist: boolean;
  addedBy: string;
  expiresAt?: string;
  createdAt: string;
}

/** Raw watchlist row from `GET/POST/PATCH /api/v1/watchlist`. */
export interface WatchlistApiEntry {
  id: string;
  watchlist_entity_type: WatchlistEntityType;
  watchlist_entity_id: string;
  watchlist_reason: string;
  risk_severity: RiskSeverity;
  is_blacklist: boolean;
  created_by: string;
  expires_at: string | null;
  created_at: string;
}

export interface WatchlistCreatePayload {
  watchlist_entity_type: WatchlistEntityType;
  watchlist_entity_id: string;
  watchlist_reason: string;
  risk_severity: RiskSeverity;
  is_blacklist: boolean;
  created_by: string;
  expires_at: string | null;
}

export interface WatchlistUpdatePayload {
  watchlist_reason?: string;
  risk_severity?: RiskSeverity;
  is_blacklist?: boolean;
  expires_at?: string | null;
}

export function isWatchlistEntryExpired(entry: WatchlistEntry): boolean {
  if (!entry.expiresAt) return false;
  return Date.parse(entry.expiresAt) <= Date.now();
}

export function mapWatchlistFromApi(row: WatchlistApiEntry): WatchlistEntry {
  return {
    id: row.id,
    entityType: row.watchlist_entity_type,
    entityId: row.watchlist_entity_id,
    reason: row.watchlist_reason,
    severity: row.risk_severity,
    isBlacklist: row.is_blacklist,
    addedBy: row.created_by,
    expiresAt: row.expires_at ?? undefined,
    createdAt: row.created_at,
  };
}

export function mapWatchlistToCreatePayload(
  entry: Omit<WatchlistEntry, 'id' | 'createdAt'>,
): WatchlistCreatePayload {
  return {
    watchlist_entity_type: entry.entityType,
    watchlist_entity_id: entry.entityId,
    watchlist_reason: entry.reason,
    risk_severity: entry.severity,
    is_blacklist: entry.isBlacklist,
    created_by: entry.addedBy,
    expires_at: entry.expiresAt ?? null,
  };
}

export function mapWatchlistToUpdatePayload(patch: {
  reason?: string;
  severity?: RiskSeverity;
  isBlacklist?: boolean;
  expiresAt?: string | null;
}): WatchlistUpdatePayload {
  return {
    ...(patch.reason !== undefined ? { watchlist_reason: patch.reason } : {}),
    ...(patch.severity !== undefined ? { risk_severity: patch.severity } : {}),
    ...(patch.isBlacklist !== undefined ? { is_blacklist: patch.isBlacklist } : {}),
    ...(patch.expiresAt !== undefined ? { expires_at: patch.expiresAt } : {}),
  };
}
