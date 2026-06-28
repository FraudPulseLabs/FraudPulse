// src/app/core/services/case.service.ts
import { Injectable, inject, signal } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import type { CaseEvent, CaseNote, CaseStatus, CaseUpdate, FraudCase, ResolutionCode } from '../models';

interface CaseApiResponse {
  id: string;
  transaction_id: string;
  title: string;
  status: CaseStatus;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  resolution_code?: ResolutionCode;
  assigned_to?: string;
  created_at: string;
  updated_at: string;
}

interface CaseNoteApiResponse {
  id: string;
  case_id: string;
  author_id: string;
  body: string;
  created_at: string;
}

interface CaseEventApiResponse {
  id: string;
  case_id: string;
  event_type: string;
  description: string;
  actor: string;
  created_at: string;
}

export interface TransactionDetail {
  id: string;
  merchantId: string;
  transactionAmount: number;
  transactionCurrency: string;
  enrichedAmountUsd: number | null;
  cardId: string | null;
  cardType: string | null;
  channel: string | null;
  decision: string | null;
  fraudScore: number | null;
  modelVersion: string | null;
  ts: string;
  transactionCountry: string | null;
  transactionCity: string | null;
  merchantCategoryCode: string | null;
  authentication: string | null;
  panEntryMode: string | null;
  reasonCode: string | null;
}

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
export class CaseService {
  private http = inject(HttpClient);
  private baseUrl     = `${environment.apiUrl}/api/v1/cases`;
  private txBaseUrl   = `${environment.apiUrl}/api/v1/transactions`;

  private _cases       = signal<FraudCase[]>([]);
  private _notes       = signal<Record<string, CaseNote[]>>({});
  private _events      = signal<Record<string, CaseEvent[]>>({});
  private _transaction = signal<Record<string, TransactionDetail>>({});

  readonly cases       = this._cases.asReadonly();
  readonly loading     = signal(false);
  readonly error       = signal<string | null>(null);

  // ==========================================================================
  // Cases
  // ==========================================================================

  load(): void {
    this.error.set(null);
    this.loading.set(true);

    this.http.get<CaseApiResponse[]>(this.baseUrl).subscribe({
      next: (res) => {
        this._cases.set(res.map(this._mapCase));
        this.loading.set(false);
      },
      error: (err) => {
        this.error.set(httpErrorMessage(err, 'Failed to load cases'));
        this.loading.set(false);
        console.error('[CaseService] load failed', err);
      },
    });
  }

  byStatus(status?: CaseStatus): FraudCase[] {
    return status ? this._cases().filter(c => c.status === status) : this._cases();
  }

  getById(id: string): FraudCase | undefined {
    return this._cases().find(c => c.id === id);
  }

  updateStatus(id: string, status: CaseStatus, resolutionCode?: ResolutionCode): void {
    this._patch(id, { status, ...(resolutionCode && { resolutionCode }) });
  }

  assign(id: string, assignedTo: string): void {
    this._patch(id, { assignedTo });
  }

  // ==========================================================================
  // Transaction detail
  // ==========================================================================

  loadTransaction(transactionId: string): void {
    if (this._transaction()[transactionId]) return; // already loaded

    this.http.get<any>(`${this.txBaseUrl}/${transactionId}`).subscribe({
      next: (raw) => this._transaction.update(all => ({
        ...all,
        [transactionId]: {
          id:                   raw.id,
          merchantId:           raw.merchant_id,
          transactionAmount:    raw.transaction_amount,
          transactionCurrency:  raw.transaction_currency,
          enrichedAmountUsd:    raw.enriched_amount_usd,
          cardId:               raw.card_id,
          cardType:             raw.card_type,
          channel:              raw.channel,
          decision:             raw.decision,
          fraudScore:           raw.fraud_score,
          modelVersion:         raw.model_version,
          ts:                   raw.ts,
          transactionCountry:   raw.transaction_country,
          transactionCity:      raw.transaction_city,
          merchantCategoryCode: raw.merchant_category_code,
          authentication:       raw.authentication,
          panEntryMode:         raw.pan_entry_mode,
          reasonCode:           raw.reason_code,
        },
      })),
      error: (err) => console.error('[CaseService] loadTransaction failed', err),
    });
  }

  transactionFor(transactionId: string): TransactionDetail | null {
    return this._transaction()[transactionId] ?? null;
  }

  // ==========================================================================
  // Notes
  // ==========================================================================

  loadNotes(caseId: string): void {
    this.http.get<CaseNoteApiResponse[]>(`${this.baseUrl}/${caseId}/notes`).subscribe({
      next: (res) => this._notes.update(all => ({ ...all, [caseId]: res.map(this._mapNote) })),
      error: (err) => console.error('[CaseService] loadNotes failed', err),
    });
  }

  notesForCase(caseId: string): CaseNote[] {
    return this._notes()[caseId] ?? [];
  }

  addNote(caseId: string, body: string, authorId: string): void {
    this.http
      .post<CaseNoteApiResponse>(`${this.baseUrl}/${caseId}/notes`, { author_id: authorId, body })
      .subscribe({
        next: (res) => {
          this._notes.update(all => ({ ...all, [caseId]: [...(all[caseId] ?? []), this._mapNote(res)] }));
          this.loadEvents(caseId);
        },
        error: (err) => console.error('[CaseService] addNote failed', err),
      });
  }

  // ==========================================================================
  // Events (timeline)
  // ==========================================================================

  loadEvents(caseId: string): void {
    this.http.get<CaseEventApiResponse[]>(`${this.baseUrl}/${caseId}/events`).subscribe({
      next: (res) => this._events.update(all => ({ ...all, [caseId]: res.map(this._mapEvent) })),
      error: (err) => console.error('[CaseService] loadEvents failed', err),
    });
  }

  eventsForCase(caseId: string): CaseEvent[] {
    return this._events()[caseId] ?? [];
  }

  // ==========================================================================
  // Mappers
  // ==========================================================================

  private _mapCase(raw: CaseApiResponse): FraudCase {
    return {
      id:             raw.id,
      transactionId:  raw.transaction_id,
      title:          raw.title,
      status:         raw.status,
      riskLevel:      raw.risk_level,
      resolutionCode: raw.resolution_code,
      assignedTo:     raw.assigned_to,
      createdAt:      raw.created_at,
      updatedAt:      raw.updated_at,
    };
  }

  private _mapNote(raw: CaseNoteApiResponse): CaseNote {
    return {
      id:        raw.id,
      caseId:    raw.case_id,
      authorId:  raw.author_id,
      body:      raw.body,
      createdAt: raw.created_at,
    };
  }

  private _mapEvent(raw: CaseEventApiResponse): CaseEvent {
    return {
      id:          raw.id,
      caseId:      raw.case_id,
      eventType:   raw.event_type as any,
      description: raw.description,
      actor:       raw.actor,
      createdAt:   raw.created_at,
    };
  }

  // ==========================================================================
  // Helpers
  // ==========================================================================

  private _patch(id: string, payload: CaseUpdate): void {
    const body: Record<string, unknown> = {};
    if (payload.status         !== undefined) body['status']          = payload.status;
    if (payload.riskLevel      !== undefined) body['risk_level']      = payload.riskLevel;
    if (payload.resolutionCode !== undefined) body['resolution_code'] = payload.resolutionCode;
    if (payload.assignedTo     !== undefined) body['assigned_to']     = payload.assignedTo;

    this.http.patch<CaseApiResponse>(`${this.baseUrl}/${id}`, body).subscribe({
      next: (res) => {
        this._cases.update(list => list.map(c => c.id === id ? this._mapCase(res) : c));
        this.loadEvents(id);
      },
      error: (err) => console.error('[CaseService] patch failed', err),
    });
  }
}