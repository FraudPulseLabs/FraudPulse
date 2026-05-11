import { Injectable, signal } from '@angular/core';
import { MOCK_METRICS } from '../mock/metrics.mock';
import type { MetricsSummary } from '../models';

@Injectable({ providedIn: 'root' })
export class MetricsService {
  private store = signal<MetricsSummary>(MOCK_METRICS);
  readonly metrics = this.store.asReadonly();

  refresh(): void {
    // TODO: Replace with HTTP polling - GET /metrics every 30s
    console.warn('[TODO] refresh metrics from API');
    this.store.set({ ...MOCK_METRICS, lastUpdated: new Date().toISOString() });
  }
}
