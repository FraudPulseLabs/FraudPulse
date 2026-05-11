import { DecimalPipe } from '@angular/common';
import { Component, OnDestroy, OnInit, inject, signal } from '@angular/core';
import { MetricsService } from '../../../core/services/metrics.service';
import type { Decision } from '../../../core/models';
import { BadgeComponent } from '../../../shared/components/badge/badge.component';

@Component({
  selector: 'app-metrics-dashboard',
  standalone: true,
  imports: [BadgeComponent, DecimalPipe],
  template: `
    <div class="page-header">
      <div>
        <h2 class="page-title">Metrics Dashboard</h2>
        <p class="text-sm text-slate-500">Operational snapshot for the fraud decision system.</p>
      </div>
      <button type="button" class="btn-secondary" (click)="manualRefresh()">Refresh</button>
    </div>

    @if (metrics(); as m) {
      <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        <div class="card-compact border-l-4" [style.border-left-color]="'var(--color-fp-accent-500)'">
          <p class="text-2xl font-bold text-slate-900">{{ m.transactionVolume.lastHour }}</p>
          <p class="text-sm text-slate-500">Transactions (1h)</p>
        </div>
        <div class="card-compact border-l-4" [style.border-left-color]="'var(--color-fp-accent-500)'">
          <p class="text-2xl font-bold text-slate-900">{{ m.transactionVolume.lastDay }}</p>
          <p class="text-sm text-slate-500">Transactions (24h)</p>
        </div>
        <div class="card-compact border-l-4" [style.border-left-color]="'var(--color-fp-review-ring)'">
          <p class="text-2xl font-bold text-slate-900">{{ m.openAlerts }}</p>
          <p class="text-sm text-slate-500">Open Alerts</p>
        </div>
        <div class="card-compact border-l-4" [style.border-left-color]="'var(--color-fp-block-ring)'">
          <p class="text-2xl font-bold text-slate-900">{{ m.activeCases }}</p>
          <p class="text-sm text-slate-500">Active Cases</p>
        </div>
      </div>

      <section class="card mt-6">
        <h3 class="section-title">Score distribution</h3>
        <div class="space-y-4">
          <div class="grid grid-cols-[90px_minmax(0,1fr)_60px] items-center gap-4">
            <span class="text-sm text-slate-500">Mean</span>
            <div class="score-bar-track"><div class="score-bar-fill" [style.width.%]="m.scoreDistribution.mean * 100" [style.background-color]="scoreColour(m.scoreDistribution.mean)"></div></div>
            <span class="text-sm font-mono">{{ m.scoreDistribution.mean | number: '1.2-2' }}</span>
          </div>
          <div class="grid grid-cols-[90px_minmax(0,1fr)_60px] items-center gap-4">
            <span class="text-sm text-slate-500">Median</span>
            <div class="score-bar-track"><div class="score-bar-fill" [style.width.%]="m.scoreDistribution.median * 100" [style.background-color]="scoreColour(m.scoreDistribution.median)"></div></div>
            <span class="text-sm font-mono">{{ m.scoreDistribution.median | number: '1.2-2' }}</span>
          </div>
          <div class="grid grid-cols-[90px_minmax(0,1fr)_60px] items-center gap-4">
            <span class="text-sm text-slate-500">P95</span>
            <div class="score-bar-track"><div class="score-bar-fill" [style.width.%]="m.scoreDistribution.p95 * 100" [style.background-color]="scoreColour(m.scoreDistribution.p95)"></div></div>
            <span class="text-sm font-mono">{{ m.scoreDistribution.p95 | number: '1.2-2' }}</span>
          </div>
        </div>
      </section>

      <section class="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-6">
        @for (decision of decisions; track decision) {
          <div class="card-compact">
            <div class="flex items-center justify-between">
              <app-badge [value]="decision" />
              <span class="text-xl font-bold text-slate-900">{{ bucket(decision).pct | number: '1.1-1' }}%</span>
            </div>
            <p class="mt-3 text-sm text-slate-500">{{ bucket(decision).count }} transactions</p>
            <div class="score-bar-track mt-3">
              <div class="score-bar-fill" [style.width.%]="bucket(decision).pct" [style.background-color]="decisionColour(decision)"></div>
            </div>
          </div>
        }
      </section>

      <section class="card mt-6">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <p class="text-sm text-slate-500">Model version</p>
            <p class="text-lg font-semibold text-slate-900">{{ m.modelVersion }}</p>
          </div>
          <div>
            <p class="text-sm text-slate-500">System status</p>
            <div class="flex items-center gap-2">
              <span
                class="w-2 h-2 rounded-full"
                [class.bg-green-500]="m.systemStatus === 'OK'"
                [class.bg-yellow-500]="m.systemStatus === 'DEGRADED'"
                [class.bg-red-500]="m.systemStatus === 'DOWN'"
              ></span>
              <span class="font-medium text-slate-900">System {{ m.systemStatus }}</span>
            </div>
          </div>
          <div>
            <p class="text-sm text-slate-500">Last refresh</p>
            <p class="font-medium text-slate-900">{{ secondsAgo() }} seconds ago</p>
          </div>
          <div>
            <p class="text-sm text-slate-500">Avg case age</p>
            <p class="font-medium text-slate-900">{{ m.avgCaseAgeDays | number: '1.1-1' }} days</p>
          </div>
        </div>
      </section>
    }
  `,
})
export class MetricsDashboardComponent implements OnInit, OnDestroy {
  private metricsService = inject(MetricsService);
  private refreshTimer: ReturnType<typeof setInterval> | null = null;
  private secondsTimer: ReturnType<typeof setInterval> | null = null;

  decisions: Decision[] = ['ALLOW', 'REVIEW', 'BLOCK'];
  metrics = this.metricsService.metrics;
  secondsAgo = signal(0);

  ngOnInit(): void {
    this.refreshTimer = setInterval(() => this.metricsService.refresh(), 30_000);
    this.secondsTimer = setInterval(() => this.secondsAgo.update((value) => value + 1), 1_000);
  }

  ngOnDestroy(): void {
    if (this.refreshTimer) clearInterval(this.refreshTimer);
    if (this.secondsTimer) clearInterval(this.secondsTimer);
  }

  manualRefresh(): void {
    // TODO: force refresh from API
    this.metricsService.refresh();
    this.secondsAgo.set(0);
  }

  bucket(decision: Decision) {
    return this.metrics().decisionSplit[decision];
  }

  scoreColour(value: number): string {
    if (value >= 0.8) return 'var(--color-fp-block-ring)';
    if (value >= 0.4) return 'var(--color-fp-review-ring)';
    return 'var(--color-fp-allow-ring)';
  }

  decisionColour(decision: Decision): string {
    const map: Record<Decision, string> = {
      ALLOW: 'var(--color-fp-allow-ring)',
      REVIEW: 'var(--color-fp-review-ring)',
      BLOCK: 'var(--color-fp-block-ring)',
    };
    return map[decision];
  }
}
