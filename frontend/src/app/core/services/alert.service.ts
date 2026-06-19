// src/app/core/services/alert.service.ts
import { Injectable, inject, signal, computed } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import type { Alert, AlertReason, AlertSeverity } from '../models/alert.model';

interface AlertListResponse {
  success: boolean;
  message: string;
  data: AlertApiResponse[];
}

// Shape returned by the backend (snake_case)
interface AlertApiResponse {
  id: string;
  transaction_id: string;
  reason: AlertReason;
  severity: AlertSeverity;
  created_at: string;
}

@Injectable({ providedIn: 'root' })
export class AlertService {
  private http = inject(HttpClient);
  private baseUrl = `${environment.apiUrl}/api/v1/alerts`;

  // All loaded alerts held in a signal
  private _alerts = signal<Alert[]>([]);

  // Public read-only view
  readonly alerts = this._alerts.asReadonly();

  // Computed: count per severity across all alerts
  readonly countBySeverity = computed(() => {
    const all = this._alerts();
    return {
      HIGH:   all.filter(a => a.severity === 'HIGH').length,
      MEDIUM: all.filter(a => a.severity === 'MEDIUM').length,
      LOW:    all.filter(a => a.severity === 'LOW').length,
    };
  });

  // Fetch alerts from the backend, optionally filtered
  load(params?: { reason?: AlertReason; severity?: AlertSeverity; transactionId?: string }): void {
    let httpParams = new HttpParams();

    if (params?.reason)        httpParams = httpParams.set('reason', params.reason);
    if (params?.severity)      httpParams = httpParams.set('severity', params.severity);
    if (params?.transactionId) httpParams = httpParams.set('transaction_id', params.transactionId);

    this.http
      .get<AlertListResponse>(this.baseUrl, { params: httpParams })
      .subscribe({
        next: (res) => this._alerts.set(res.data.map(this._map)),
        error: (err) => console.error('[AlertService] load failed', err),
      });
  }

  // Filter alerts by severity — used by components that need a subset
  bySeverity(severity?: AlertSeverity): Alert[] {
    const all = this._alerts();
    return severity ? all.filter(a => a.severity === severity) : all;
  }

  // Fetch a single alert by id from the already-loaded list.
  // Falls back to the API if not found locally.
  getById(id: string): Alert | undefined {
    return this._alerts().find(a => a.id === id);
  }

  // Kept for backward compatibility with components that used byStatus —
  // alerts no longer have status, so this returns all alerts.
  // Components relying on this should migrate to bySeverity().
  byStatus(_status?: string): Alert[] {
    return this._alerts();
  }

  // Maps snake_case API response to camelCase model
  private _map(raw: AlertApiResponse): Alert {
    return {
      id:            raw.id,
      transactionId: raw.transaction_id,
      reason:        raw.reason,
      severity:      raw.severity,
      createdAt:     raw.created_at,
    };
  }
}