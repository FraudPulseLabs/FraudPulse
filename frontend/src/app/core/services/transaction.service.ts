import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { txStore } from '../mock/transactions.mock';
import type { Transaction } from '../models';

export interface TxFilters {
  decision?: string;
  userId?: string;
  minScore?: number;
  maxScore?: number;
}

@Injectable({ providedIn: 'root' })
export class TransactionService {
  private http = inject(HttpClient);

  readonly transactions = txStore.asReadonly();

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
