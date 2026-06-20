import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { CaseService } from './case.service';
import { environment } from '../../../environments/environment';

describe('CaseService', () => {
  let service: CaseService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [CaseService, provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(CaseService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('loads cases and maps API fields', () => {
    service.load();

    const req = http.expectOne(`${environment.apiUrl}/api/v1/cases`);
    req.flush([
      {
        id: 'case-1',
        transaction_id: 'tx-1',
        title: 'ATM cash-out surge',
        status: 'OPEN',
        risk_level: 'HIGH',
        created_at: '2026-06-01T12:00:00Z',
        updated_at: '2026-06-02T12:00:00Z',
      },
    ]);

    expect(service.loading()).toBe(false);
    expect(service.cases()).toHaveLength(1);
    expect(service.cases()[0].title).toBe('ATM cash-out surge');
    expect(service.cases()[0].riskLevel).toBe('HIGH');
  });

  it('filters cases by status', () => {
    service.load();
    http.expectOne(`${environment.apiUrl}/api/v1/cases`).flush([
      {
        id: '1',
        transaction_id: 'a',
        title: 'Open case',
        status: 'OPEN',
        risk_level: 'MEDIUM',
        created_at: '2026-06-01T12:00:00Z',
        updated_at: '2026-06-01T12:00:00Z',
      },
      {
        id: '2',
        transaction_id: 'b',
        title: 'Closed case',
        status: 'CLOSED',
        risk_level: 'LOW',
        resolution_code: 'FALSE_POSITIVE',
        created_at: '2026-06-01T12:00:00Z',
        updated_at: '2026-06-01T12:00:00Z',
      },
    ]);

    expect(service.byStatus('OPEN')).toHaveLength(1);
    expect(service.byStatus()).toHaveLength(2);
  });

  it('patches case status', () => {
    service.load();
    http.expectOne(`${environment.apiUrl}/api/v1/cases`).flush([
      {
        id: 'case-1',
        transaction_id: 'tx-1',
        title: 'Investigation',
        status: 'OPEN',
        risk_level: 'MEDIUM',
        created_at: '2026-06-01T12:00:00Z',
        updated_at: '2026-06-01T12:00:00Z',
      },
    ]);

    service.updateStatus('case-1', 'INVESTIGATING');

    const patchReq = http.expectOne(`${environment.apiUrl}/api/v1/cases/case-1`);
    expect(patchReq.request.method).toBe('PATCH');
    expect(patchReq.request.body).toEqual({ status: 'INVESTIGATING' });
    patchReq.flush({
      id: 'case-1',
      transaction_id: 'tx-1',
      title: 'Investigation',
      status: 'INVESTIGATING',
      risk_level: 'MEDIUM',
      created_at: '2026-06-01T12:00:00Z',
      updated_at: '2026-06-02T12:00:00Z',
    });

    const eventsReq = http.expectOne(`${environment.apiUrl}/api/v1/cases/case-1/events`);
    eventsReq.flush([]);
  });
});
