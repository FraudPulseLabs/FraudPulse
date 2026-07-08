import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { AlertService } from './alert.service';
import { environment } from '../../../environments/environment';

describe('AlertService', () => {
  let service: AlertService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [AlertService, provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(AlertService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('loads alerts and maps snake_case fields', () => {
    service.load();
    expect(service.loading()).toBe(true);

    const req = http.expectOne(`${environment.apiUrl}/api/v1/alerts`);
    expect(req.request.method).toBe('GET');
    req.flush({
      success: true,
      message: 'ok',
      data: [
        {
          id: 'alert-1',
          transaction_id: 'tx-1',
          reason: 'FRAUD_REVIEW_REQUIRED',
          severity: 'HIGH',
          created_at: '2026-06-01T12:00:00Z',
        },
      ],
    });

    expect(service.loading()).toBe(false);
    expect(service.error()).toBeNull();
    expect(service.alerts()).toHaveLength(1);
    expect(service.alerts()[0]).toEqual({
      id: 'alert-1',
      transactionId: 'tx-1',
      reason: 'FRAUD_REVIEW_REQUIRED',
      severity: 'HIGH',
      createdAt: '2026-06-01T12:00:00Z',
    });
    expect(service.countBySeverity().HIGH).toBe(1);
  });

  it('passes filter query params', () => {
    service.load({ severity: 'HIGH', reason: 'FRAUD_SCORE_DECLINE' });

    const req = http.expectOne(
      (r) =>
        r.url === `${environment.apiUrl}/api/v1/alerts` &&
        r.params.get('severity') === 'HIGH' &&
        r.params.get('reason') === 'FRAUD_SCORE_DECLINE',
    );
    req.flush({ success: true, message: 'ok', data: [] });
  });

  it('sets error on HTTP failure', () => {
    service.load();

    const req = http.expectOne(`${environment.apiUrl}/api/v1/alerts`);
    req.flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });

    expect(service.loading()).toBe(false);
    expect(service.error()).toBe('Unauthorized');
  });

  it('filters alerts by severity', () => {
    service.load();
    http.expectOne(`${environment.apiUrl}/api/v1/alerts`).flush({
      success: true,
      message: 'ok',
      data: [
        {
          id: '1',
          transaction_id: 'a',
          reason: 'FRAUD_REVIEW_REQUIRED',
          severity: 'HIGH',
          created_at: '2026-06-01T12:00:00Z',
        },
        {
          id: '2',
          transaction_id: 'b',
          reason: 'FRAUD_REVIEW_REQUIRED',
          severity: 'LOW',
          created_at: '2026-06-01T12:00:00Z',
        },
      ],
    });

    expect(service.bySeverity('HIGH')).toHaveLength(1);
    expect(service.getById('2')?.severity).toBe('LOW');
  });
});
