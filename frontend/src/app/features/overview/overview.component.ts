import { Component, OnInit, computed, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AlertService } from '../../core/services/alert.service';
import { CaseService } from '../../core/services/case.service';
import { TransactionService } from '../../core/services/transaction.service';
import { WatchlistService } from '../../core/services/watchlist.service';
import { isWatchlistEntryExpired } from '../../core/models/watchlist.model';
import { BadgeComponent } from '../../shared/components/badge/badge.component';
import { TimeAgoPipe } from '../../shared/pipes/time-ago.pipe';

@Component({
  selector: 'app-overview',
  standalone: true,
  imports: [RouterLink, BadgeComponent, TimeAgoPipe],
  template: `
    <div class="page-header">
      <div>
        <h2 class="page-title">Operations Overview</h2>
        <p class="text-sm fp-text-secondary">
          Summary of live fraud detection activity across transactions, alerts, and investigations.
        </p>
      </div>
    </div>

    @if (loadError()) {
      <div class="card mb-4 border border-red-200 bg-red-50 text-sm text-red-700">{{ loadError() }}</div>
    }

    @if (loading()) {
      <p class="text-sm fp-text-secondary">Loading dashboard…</p>
    } @else {
      <div class="fp-stat-grid">
        <a routerLink="/transactions" class="card-compact border-l-4 hover:opacity-90 transition-opacity" style="border-left-color: var(--color-fp-accent-500)">
          <p class="fp-stat-value">{{ transactionCount() }}</p>
          <p class="fp-stat-label">Recent transactions</p>
        </a>
        <a routerLink="/alerts" class="card-compact border-l-4 hover:opacity-90 transition-opacity" style="border-left-color: var(--color-fp-review-ring)">
          <p class="fp-stat-value">{{ alertCount() }}</p>
          <p class="fp-stat-label">Open alerts</p>
        </a>
        <a routerLink="/cases" class="card-compact border-l-4 hover:opacity-90 transition-opacity" style="border-left-color: var(--color-fp-block-ring)">
          <p class="fp-stat-value">{{ activeCaseCount() }}</p>
          <p class="fp-stat-label">Active cases</p>
        </a>
        <a routerLink="/watchlist" class="card-compact border-l-4 hover:opacity-90 transition-opacity" style="border-left-color: var(--fp-border)">
          <p class="fp-stat-value">{{ watchlistCount() }}</p>
          <p class="fp-stat-label">Watchlist entries</p>
        </a>
      </div>

      <div class="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <section class="card">
          <div class="mb-4 flex items-center justify-between gap-3">
            <h3 class="section-title !mb-0">Priority alerts</h3>
            <a routerLink="/alerts" class="text-xs font-medium fp-text-secondary hover:underline">View all</a>
          </div>
          @if (priorityAlerts().length === 0) {
            <p class="text-sm fp-text-secondary">No high-severity alerts at this time.</p>
          } @else {
            <ul class="divide-y" style="border-color: var(--fp-border)">
              @for (alert of priorityAlerts(); track alert.id) {
                <li class="flex items-center justify-between gap-3 py-3 first:pt-0 last:pb-0">
                  <div class="min-w-0">
                    <p class="truncate text-sm fp-text-primary">{{ alert.reason }}</p>
                    <p class="truncate text-xs fp-data-mono fp-text-secondary">{{ alert.transactionId }}</p>
                  </div>
                  <div class="shrink-0 text-right">
                    <app-badge [value]="alert.severity" />
                    <p class="mt-1 text-xs fp-text-muted">{{ alert.createdAt | timeAgo }}</p>
                  </div>
                </li>
              }
            </ul>
          }
        </section>

        <section class="card">
          <div class="mb-4 flex items-center justify-between gap-3">
            <h3 class="section-title !mb-0">Active investigations</h3>
            <a routerLink="/cases" class="text-xs font-medium fp-text-secondary hover:underline">View all</a>
          </div>
          @if (activeCases().length === 0) {
            <p class="text-sm fp-text-secondary">No open or in-progress cases.</p>
          } @else {
            <ul class="divide-y" style="border-color: var(--fp-border)">
              @for (c of activeCases(); track c.id) {
                <li>
                  <a
                    [routerLink]="['/cases', c.id]"
                    class="flex items-center justify-between gap-3 py-3 first:pt-0 last:pb-0 hover:bg-[var(--fp-hover)] -mx-2 px-2 rounded-sm transition-colors"
                  >
                    <div class="min-w-0">
                      <p class="truncate text-sm fp-text-primary">{{ c.title }}</p>
                      <p class="truncate text-xs fp-data-mono fp-text-secondary">{{ c.id }}</p>
                    </div>
                    <div class="shrink-0 text-right">
                      <app-badge [value]="c.status" />
                      <p class="mt-1 text-xs fp-text-muted">{{ c.createdAt | timeAgo }}</p>
                    </div>
                  </a>
                </li>
              }
            </ul>
          }
        </section>
      </div>

      <section class="card mt-6">
        <h3 class="section-title">Workflow</h3>
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          @for (step of workflowSteps; track step.path) {
            <a
              [routerLink]="step.path"
              class="rounded-sm border p-4 transition-colors hover:bg-[var(--fp-hover)]"
              style="border-color: var(--fp-border)"
            >
              <p class="text-sm font-semibold fp-text-primary">{{ step.label }}</p>
              <p class="mt-1 text-xs fp-text-secondary">{{ step.description }}</p>
            </a>
          }
        </div>
      </section>
    }
  `,
})
export class OverviewComponent implements OnInit {
  private alertService = inject(AlertService);
  private caseService = inject(CaseService);
  private txService = inject(TransactionService);
  private watchlistService = inject(WatchlistService);

  readonly loading = computed(
    () =>
      this.alertService.loading() ||
      this.caseService.loading() ||
      this.txService.loading() ||
      this.watchlistService.loading(),
  );

  readonly loadError = computed(
    () =>
      this.alertService.error() ||
      this.caseService.error() ||
      this.txService.error() ||
      this.watchlistService.error(),
  );

  readonly transactionCount = computed(() => this.txService.transactions().length);
  readonly alertCount = computed(() => this.alertService.alerts().length);
  readonly activeCaseCount = computed(
    () =>
      this.caseService.cases().filter((c) => c.status === 'OPEN' || c.status === 'INVESTIGATING')
        .length,
  );
  readonly watchlistCount = computed(
    () =>
      this.watchlistService.entries().filter((e) => !isWatchlistEntryExpired(e)).length,
  );

  readonly priorityAlerts = computed(() =>
    [...this.alertService.alerts()]
      .filter((a) => a.severity === 'HIGH')
      .sort((a, b) => Date.parse(b.createdAt) - Date.parse(a.createdAt))
      .slice(0, 5),
  );

  readonly activeCases = computed(() =>
    [...this.caseService.cases()]
      .filter((c) => c.status === 'OPEN' || c.status === 'INVESTIGATING')
      .sort((a, b) => Date.parse(b.updatedAt) - Date.parse(a.updatedAt))
      .slice(0, 5),
  );

  readonly workflowSteps = [
    {
      path: '/transactions',
      label: 'Monitor transactions',
      description: 'Review scored payments and decision outcomes.',
    },
    {
      path: '/alerts',
      label: 'Triage alerts',
      description: 'Prioritise high-risk signals from the engine.',
    },
    {
      path: '/cases',
      label: 'Investigate cases',
      description: 'Document findings and resolve investigations.',
    },
    {
      path: '/watchlist',
      label: 'Manage watchlist',
      description: 'Flag merchants and entities for enhanced scrutiny.',
    },
  ];

  ngOnInit(): void {
    this.alertService.load();
    this.caseService.load();
    void this.txService.loadTransactions();
    void this.watchlistService.loadEntries();
  }
}
