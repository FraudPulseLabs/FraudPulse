import { Component, OnInit, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { OverviewService } from '../../core/services/overview.service';
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

    <!-- Stat cards -->
    @if (loading()) {
      <div class="fp-stat-grid">
        @for (i of [1, 2, 3, 4]; track i) {
          <div class="card-compact border-l-4" style="border-left-color: var(--fp-border)">
            <div class="fp-skeleton h-7 w-16"></div>
            <div class="fp-skeleton mt-2 h-3 w-28"></div>
          </div>
        }
      </div>
    } @else {
      <div class="fp-stat-grid">
        <a routerLink="/transactions" class="card-compact border-l-4 hover:opacity-90 transition-opacity" style="border-left-color: var(--color-fp-accent-500)">
          <p class="fp-stat-value">{{ counts().recentTransactions }}</p>
          <p class="fp-stat-label">Recent transactions</p>
        </a>
        <a routerLink="/alerts" class="card-compact border-l-4 hover:opacity-90 transition-opacity" style="border-left-color: var(--color-fp-review-ring)">
          <p class="fp-stat-value">{{ counts().openAlerts }}</p>
          <p class="fp-stat-label">Open alerts</p>
        </a>
        <a routerLink="/cases" class="card-compact border-l-4 hover:opacity-90 transition-opacity" style="border-left-color: var(--color-fp-block-ring)">
          <p class="fp-stat-value">{{ counts().activeCases }}</p>
          <p class="fp-stat-label">Active cases</p>
        </a>
        <a routerLink="/watchlist" class="card-compact border-l-4 hover:opacity-90 transition-opacity" style="border-left-color: var(--fp-border)">
          <p class="fp-stat-value">{{ counts().watchlistEntries }}</p>
          <p class="fp-stat-label">Watchlist entries</p>
        </a>
      </div>
    }

    <!-- Priority alerts + active investigations -->
    <div class="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
      <section class="card">
        <div class="mb-4 flex items-center justify-between gap-3">
          <h3 class="section-title !mb-0">Priority alerts</h3>
          <a routerLink="/alerts" class="text-xs font-medium fp-text-secondary hover:underline">View all</a>
        </div>
        @if (loading()) {
          <ul class="divide-y" style="border-color: var(--fp-border)">
            @for (i of [1, 2, 3]; track i) {
              <li class="flex items-center justify-between gap-3 py-3 first:pt-0 last:pb-0">
                <div class="min-w-0 flex-1">
                  <div class="fp-skeleton h-4 w-3/4"></div>
                  <div class="fp-skeleton mt-2 h-3 w-1/3"></div>
                </div>
                <div class="fp-skeleton h-5 w-14 rounded-full"></div>
              </li>
            }
          </ul>
        } @else if (priorityAlerts().length === 0) {
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
        @if (loading()) {
          <ul class="divide-y" style="border-color: var(--fp-border)">
            @for (i of [1, 2, 3]; track i) {
              <li class="flex items-center justify-between gap-3 py-3 first:pt-0 last:pb-0">
                <div class="min-w-0 flex-1">
                  <div class="fp-skeleton h-4 w-2/3"></div>
                  <div class="fp-skeleton mt-2 h-3 w-2/5"></div>
                </div>
                <div class="fp-skeleton h-5 w-16 rounded-full"></div>
              </li>
            }
          </ul>
        } @else if (activeCases().length === 0) {
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
  `,
})
export class OverviewComponent implements OnInit {
  private overview = inject(OverviewService);

  readonly loading = this.overview.loading;
  readonly loadError = this.overview.error;
  readonly counts = this.overview.counts;
  readonly priorityAlerts = this.overview.priorityAlerts;
  readonly activeCases = this.overview.activeCases;

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
    this.overview.load();
  }
}
