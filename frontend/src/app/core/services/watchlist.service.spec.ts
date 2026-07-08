import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { WatchlistService } from './watchlist.service';
import { watchlistStore } from '../stores/watchlist.store';
import { environment } from '../../../environments/environment';

describe('WatchlistService', () => {
  let service: WatchlistService;
  let http: HttpTestingController;

  beforeEach(() => {
    watchlistStore.set([]);
    TestBed.configureTestingModule({
      providers: [WatchlistService, provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(WatchlistService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('loads entries from API into the store', async () => {
    const loadPromise = service.loadEntries();

    const req = http.expectOne(
      (r) =>
        r.url === `${environment.apiUrl}/api/v1/watchlist` &&
        r.params.get('include_expired') === 'false',
    );
    req.flush({
      success: true,
      message: 'ok',
      data: [
        {
          id: 'wl-1',
          watchlist_entity_type: 'MERCHANT',
          watchlist_entity_id: 'merch_test_001',
          watchlist_reason: 'ATM cluster',
          risk_severity: 'HIGH',
          is_blacklist: true,
          created_by: 'analyst@test.com',
          expires_at: null,
          created_at: '2026-06-01T12:00:00Z',
        },
      ],
    });

    await loadPromise;

    expect(service.entries()).toHaveLength(1);
    expect(service.entries()[0].entityId).toBe('merch_test_001');
    expect(service.entries()[0].isBlacklist).toBe(true);
  });

  it('adds a watchlist entry via POST', async () => {
    const created = service.add({
      entityType: 'MERCHANT',
      entityId: 'MERCH-9',
      reason: 'Velocity',
      severity: 'MEDIUM',
      isBlacklist: false,
      addedBy: 'analyst@test.com',
    });

    const req = http.expectOne(`${environment.apiUrl}/api/v1/watchlist`);
    expect(req.request.method).toBe('POST');
    req.flush({
      success: true,
      message: 'created',
      data: {
        id: 'wl-9',
        watchlist_entity_type: 'MERCHANT',
        watchlist_entity_id: 'MERCH-9',
        watchlist_reason: 'Velocity',
        risk_severity: 'MEDIUM',
        is_blacklist: false,
        created_by: 'analyst@test.com',
        expires_at: null,
        created_at: '2026-06-01T12:00:00Z',
      },
    });

    const entry = await created;
    expect(entry.id).toBe('wl-9');
    expect(service.isWatchlisted('MERCHANT', 'MERCH-9')).toBe(true);
  });
});
