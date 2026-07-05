import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { OverviewComponent } from './overview.component';
import { OverviewService, OverviewCounts } from '../../core/services/overview.service';
import { signal } from '@angular/core';

describe('OverviewComponent', () => {
  let fixture: ComponentFixture<OverviewComponent>;

  const emptyCounts: OverviewCounts = {
    recentTransactions: 0,
    openAlerts: 0,
    activeCases: 0,
    watchlistEntries: 0,
  };

  const overviewService = {
    load: jest.fn(),
    loading: signal(false),
    error: signal<string | null>(null),
    counts: signal<OverviewCounts>(emptyCounts),
    priorityAlerts: signal([]),
    activeCases: signal([]),
  };

  beforeEach(async () => {
    overviewService.load.mockClear();

    await TestBed.configureTestingModule({
      imports: [OverviewComponent],
      providers: [
        provideRouter([]),
        { provide: OverviewService, useValue: overviewService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(OverviewComponent);
  });

  it('loads dashboard data on init', () => {
    fixture.detectChanges();

    expect(overviewService.load).toHaveBeenCalled();
  });

  it('renders the operations overview heading', () => {
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Operations Overview');
  });
});
