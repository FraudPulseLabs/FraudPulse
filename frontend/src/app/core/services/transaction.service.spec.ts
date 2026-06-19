import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TransactionService } from './transaction.service';
import { txStore } from '../stores/transaction.store';
import { environment } from '../../../environments/environment';

describe('TransactionService', () => {
  let service: TransactionService;
  let http: HttpTestingController;

  beforeEach(() => {
    txStore.set([]);
    TestBed.configureTestingModule({
      providers: [TransactionService, provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(TransactionService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('loads transactions and maps decisions', async () => {
    const loadPromise = service.loadTransactions();

    const req = http.expectOne(`${environment.apiUrl}/api/v1/transactions`);
    req.flush([
      {
        id: 'tx-1',
        transaction_amount: 200000,
        transaction_currency: 'KES',
        merchant_id: 'merch_test_001',
        ts: '2026-06-01T12:00:00Z',
        decision: 'APPROVE_WITH_REVIEW',
        lifecycle_status: 'AUTHORIZED',
        is_simulated: false,
        is_manually_created: false,
        card_id: 'card_test_001',
        score: 0.42,
        model_version: 'version2',
      },
    ]);

    await loadPromise;

    expect(service.transactions()).toHaveLength(1);
    expect(service.transactions()[0].decision).toBe('REVIEW');
    expect(service.transactions()[0].merchant).toBe('merch_test_001');
  });

  it('filters transactions client-side', async () => {
    const loadPromise = service.loadTransactions();
    http.expectOne(`${environment.apiUrl}/api/v1/transactions`).flush([
      {
        id: 'tx-1',
        transaction_amount: 100,
        transaction_currency: 'KES',
        merchant_id: 'A',
        ts: '2026-06-01T12:00:00Z',
        decision: 'APPROVE',
        lifecycle_status: 'AUTHORIZED',
        is_simulated: false,
        is_manually_created: false,
        card_id: 'card-1',
        score: 0.1,
        model_version: 'version2',
      },
      {
        id: 'tx-2',
        transaction_amount: 200,
        transaction_currency: 'KES',
        merchant_id: 'B',
        ts: '2026-06-01T13:00:00Z',
        decision: 'DECLINE',
        lifecycle_status: 'AUTHORIZED',
        is_simulated: false,
        is_manually_created: false,
        card_id: 'card-2',
        score: 0.9,
        model_version: 'version2',
      },
    ]);
    await loadPromise;

    const blocked = service.filtered({ decision: 'BLOCK' });
    expect(blocked).toHaveLength(1);
    expect(blocked[0].id).toBe('tx-2');
  });
});
