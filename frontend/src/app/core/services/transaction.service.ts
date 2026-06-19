import { Injectable, inject, signal } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { environment } from '../../../environments/environment';
import { txStore } from '../stores/transaction.store';
import type { Transaction, TransactionApiRead, TransactionDetailApiRead } from '../models';
import { mapTransactionDetailFromApi, mapTransactionFromApi } from '../models/transaction.model';

export interface TxFilters {
  decision?: string;
  userId?: string;
  minScore?: number;
  maxScore?: number;
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
export class TransactionService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/api/v1/transactions`;

  readonly transactions = txStore.asReadonly();
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);

  filtered(filters: TxFilters): Transaction[] {
    return txStore().filter(
      (t) =>
        (!filters.decision || t.decision === filters.decision) &&
        (!filters.userId || t.userId.toLowerCase().includes(filters.userId.toLowerCase())) &&
        (filters.minScore == null || t.score >= filters.minScore) &&
        (filters.maxScore == null || t.score <= filters.maxScore),
    );
  }

  getById(id: string): Transaction | undefined {
    return txStore().find((t) => t.id === id);
  }

  async loadTransactions(): Promise<void> {
    this.error.set(null);
    this.loading.set(true);
    try {
      const rows = await firstValueFrom(
        this.http.get<TransactionApiRead[]>(this.baseUrl),
      );
      txStore.set(rows.map(mapTransactionFromApi));
    } catch (err: unknown) {
      const message = httpErrorMessage(err, 'Failed to load transactions');
      this.error.set(message);
      throw err;
    } finally {
      this.loading.set(false);
    }
  }

  async fetchTransactionById(id: string): Promise<Transaction | undefined> {
    this.error.set(null);

    try {
      const row = await firstValueFrom(
        this.http.get<TransactionDetailApiRead>(`${this.baseUrl}/${encodeURIComponent(id)}`),
      );
      const mapped = mapTransactionDetailFromApi(row);
      txStore.update((list) => {
        const index = list.findIndex((t) => t.id === id);
        if (index === -1) return [mapped, ...list];
        return list.map((t) => (t.id === id ? mapped : t));
      });
      return mapped;
    } catch (err: unknown) {
      const message = httpErrorMessage(err, 'Failed to load transaction');
      this.error.set(message);
      throw err;
    }
  }

  settleTransaction(id: string): void {
    // TODO: PATCH /transactions/:id { lifecycleStatus: 'SETTLED' }
    console.warn('[TODO] settle transaction', id);
    txStore.update((list) =>
      list.map((t) => (t.id === id ? { ...t, lifecycleStatus: 'SETTLED' as const } : t)),
    );
  }

  rescoreTransaction(id: string): void {
    // TODO: POST /transactions/:id/rescore
    console.warn('[TODO] rescore transaction', id);
  }
}
