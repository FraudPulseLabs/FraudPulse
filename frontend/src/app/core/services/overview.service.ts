import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { environment } from '../../../environments/environment';
import type { Alert, AlertReason, AlertSeverity } from '../models/alert.model';
import type { CaseStatus, FraudCase } from '../models/case.model';

/**
 * Single aggregated call for the operations overview. The backend does the
 * counting and returns the two short record lists shown above the fold, so the
 * overview no longer fans out to four separate services on load. Full records
 * are fetched from the dedicated endpoints when the analyst opens a card.
 */

export interface OverviewCounts {
  recentTransactions: number;
  openAlerts: number;
  activeCases: number;
  watchlistEntries: number;
}

interface OverviewCountsApi {
  recent_transactions: number;
  open_alerts: number;
  active_cases: number;
  watchlist_entries: number;
}

interface AlertApi {
  id: string;
  transaction_id: string;
  reason: AlertReason;
  severity: AlertSeverity;
  created_at: string;
}

interface CaseApi {
  id: string;
  transaction_id: string;
  title: string;
  status: CaseStatus;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  created_at: string;
  updated_at: string;
}

interface OverviewSummaryApi {
  counts: OverviewCountsApi;
  priority_alerts: AlertApi[];
  active_cases: CaseApi[];
}

const EMPTY_COUNTS: OverviewCounts = {
  recentTransactions: 0,
  openAlerts: 0,
  activeCases: 0,
  watchlistEntries: 0,
};

function httpErrorMessage(err: unknown, fallback: string): string {
  if (err instanceof HttpErrorResponse) {
    if (err.status === 0) {
      return 'Cannot reach the API. Is the backend running? (CORS/network)';
    }
    const body = err.error as { detail?: string; message?: string } | null;
    if (typeof body?.detail === 'string') return body.detail;
    if (typeof body?.message === 'string') return body.message;
    return err.message || fallback;
  }
  if (err instanceof Error) return err.message;
  return fallback;
}

@Injectable({ providedIn: 'root' })
export class OverviewService {
  private http = inject(HttpClient);
  private baseUrl = `${environment.apiUrl}/api/v1/overview`;

  readonly loading = signal(false);
  readonly error = signal<string | null>(null);
  readonly counts = signal<OverviewCounts>(EMPTY_COUNTS);
  readonly priorityAlerts = signal<Alert[]>([]);
  readonly activeCases = signal<FraudCase[]>([]);

  load(): void {
    this.error.set(null);
    this.loading.set(true);

    this.http.get<OverviewSummaryApi>(this.baseUrl).subscribe({
      next: (res) => {
        this.counts.set({
          recentTransactions: res.counts.recent_transactions,
          openAlerts: res.counts.open_alerts,
          activeCases: res.counts.active_cases,
          watchlistEntries: res.counts.watchlist_entries,
        });
        this.priorityAlerts.set(res.priority_alerts.map(mapAlert));
        this.activeCases.set(res.active_cases.map(mapCase));
        this.loading.set(false);
      },
      error: (err) => {
        this.error.set(httpErrorMessage(err, 'Failed to load overview'));
        this.loading.set(false);
        console.error('[OverviewService] load failed', err);
      },
    });
  }
}

function mapAlert(raw: AlertApi): Alert {
  return {
    id: raw.id,
    transactionId: raw.transaction_id,
    reason: raw.reason,
    severity: raw.severity,
    createdAt: raw.created_at,
  };
}

function mapCase(raw: CaseApi): FraudCase {
  return {
    id: raw.id,
    transactionId: raw.transaction_id,
    title: raw.title,
    status: raw.status,
    riskLevel: raw.risk_level,
    createdAt: raw.created_at,
    updatedAt: raw.updated_at,
  };
}
