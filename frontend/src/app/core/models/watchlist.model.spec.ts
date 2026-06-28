import {
  isWatchlistEntryExpired,
  mapWatchlistFromApi,
  mapWatchlistToCreatePayload,
  mapWatchlistToUpdatePayload,
} from './watchlist.model';

describe('watchlist.model', () => {
  it('maps API rows to frontend entries', () => {
    const entry = mapWatchlistFromApi({
      id: 'wl-1',
      watchlist_entity_type: 'MERCHANT',
      watchlist_entity_id: 'MERCH-1',
      watchlist_reason: 'High chargebacks',
      risk_severity: 'HIGH',
      is_blacklist: true,
      created_by: 'analyst@test.com',
      expires_at: '2026-12-31T00:00:00Z',
      created_at: '2026-06-01T00:00:00Z',
    });

    expect(entry.entityType).toBe('MERCHANT');
    expect(entry.entityId).toBe('MERCH-1');
    expect(entry.expiresAt).toBe('2026-12-31T00:00:00Z');
  });

  it('detects expired entries', () => {
    const expired = isWatchlistEntryExpired({
      id: 'wl-1',
      entityType: 'MERCHANT',
      entityId: 'MERCH-1',
      reason: 'Old',
      severity: 'LOW',
      isBlacklist: false,
      addedBy: 'analyst@test.com',
      expiresAt: '2020-01-01T00:00:00Z',
      createdAt: '2019-01-01T00:00:00Z',
    });

    expect(expired).toBe(true);
  });

  it('builds create and update payloads', () => {
    const create = mapWatchlistToCreatePayload({
      entityType: 'USER',
      entityId: 'card-1',
      reason: 'Velocity',
      severity: 'MEDIUM',
      isBlacklist: false,
      addedBy: 'analyst@test.com',
    });

    expect(create.watchlist_entity_type).toBe('USER');
    expect(create.watchlist_entity_id).toBe('card-1');

    const update = mapWatchlistToUpdatePayload({
      reason: 'Updated reason',
      severity: 'HIGH',
    });

    expect(update).toEqual({
      watchlist_reason: 'Updated reason',
      risk_severity: 'HIGH',
    });
  });
});
