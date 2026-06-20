import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { OverviewComponent } from './overview.component';
import { AlertService } from '../../core/services/alert.service';
import { CaseService } from '../../core/services/case.service';
import { TransactionService } from '../../core/services/transaction.service';
import { WatchlistService } from '../../core/services/watchlist.service';
import { signal } from '@angular/core';

describe('OverviewComponent', () => {
  let fixture: ComponentFixture<OverviewComponent>;

  const alertService = {
    load: jest.fn(),
    loading: signal(false),
    error: signal<string | null>(null),
    alerts: signal([]),
    countBySeverity: signal({ HIGH: 0, MEDIUM: 0, LOW: 0 }),
  };

  const caseService = {
    load: jest.fn(),
    loading: signal(false),
    error: signal<string | null>(null),
    cases: signal([]),
  };

  const txService = {
    loadTransactions: jest.fn().mockResolvedValue(undefined),
    loading: signal(false),
    error: signal<string | null>(null),
    transactions: signal([]),
  };

  const watchlistService = {
    loadEntries: jest.fn().mockResolvedValue(undefined),
    loading: signal(false),
    error: signal<string | null>(null),
    entries: signal([]),
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [OverviewComponent],
      providers: [
        provideRouter([]),
        { provide: AlertService, useValue: alertService },
        { provide: CaseService, useValue: caseService },
        { provide: TransactionService, useValue: txService },
        { provide: WatchlistService, useValue: watchlistService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(OverviewComponent);
  });

  it('loads all dashboard data on init', () => {
    fixture.detectChanges();

    expect(alertService.load).toHaveBeenCalled();
    expect(caseService.load).toHaveBeenCalled();
    expect(txService.loadTransactions).toHaveBeenCalled();
    expect(watchlistService.loadEntries).toHaveBeenCalled();
  });

  it('renders the operations overview heading', () => {
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Operations Overview');
  });
});
