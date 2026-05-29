import { Injectable, inject, signal } from '@angular/core';
import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { environment } from '../../../environments/environment';
import { MOCK_WATCHLIST, watchlistStore } from '../mock/watchlist.mock';
import type { ApiResponse } from '../models/api-response.model';
import type {
  WatchlistApiEntry,
  WatchlistCreatePayload,
  WatchlistEntityType,
  WatchlistEntry,
  WatchlistUpdatePayload,
} from '../models';
import { mapWatchlistFromApi } from '../models/watchlist.model';

const CREATED_BY = 'fraud_analyst_01';

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
export class WatchlistService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/api/v1/watchlist`;

  readonly entries = watchlistStore.asReadonly();
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);

  isWatchlisted(entityType: WatchlistEntityType, entityId: string): boolean {
    return watchlistStore().some((e) => e.entityType === entityType && e.entityId === entityId);
  }

  async loadEntries(options?: { includeExpired?: boolean; entityType?: WatchlistEntityType }): Promise<void> {
    this.error.set(null);
    this.loading.set(true);
    try {
      if (environment.useMock) {
        watchlistStore.set([...MOCK_WATCHLIST]);
        return;
      }

      let params = new HttpParams().set(
        'include_expired',
        String(options?.includeExpired ?? false),
      );
      if (options?.entityType) {
        params = params.set('entity_type', options.entityType);
      }

      const res = await firstValueFrom(
        this.http.get<ApiResponse<WatchlistApiEntry[]>>(this.baseUrl, { params }),
      );
      if (!res.success) {
        throw new Error(res.message || 'Failed to load watchlist');
      }
      watchlistStore.set((res.data ?? []).map(mapWatchlistFromApi));
    } catch (err: unknown) {
      const message = httpErrorMessage(err, 'Failed to load watchlist');
      this.error.set(message);
      throw err;
    } finally {
      this.loading.set(false);
    }
  }

  async add(entry: Omit<WatchlistEntry, 'id' | 'createdAt'>): Promise<WatchlistEntry> {
    this.error.set(null);
    const payload: WatchlistCreatePayload = {
      watchlist_entity_type: entry.entityType,
      watchlist_entity_id: entry.entityId,
      watchlist_reason: entry.reason,
      risk_severity: entry.severity,
      is_blacklist: entry.isBlacklist,
      created_by: entry.addedBy || CREATED_BY,
      expires_at: entry.expiresAt ?? null,
    };

    if (environment.useMock) {
      const newEntry: WatchlistEntry = {
        ...entry,
        addedBy: entry.addedBy || CREATED_BY,
        id: `WL-${Date.now()}`,
        createdAt: new Date().toISOString(),
      };
      watchlistStore.update((list) => [newEntry, ...list]);
      return newEntry;
    }

    const res = await firstValueFrom(
      this.http.post<ApiResponse<WatchlistApiEntry>>(this.baseUrl, payload),
    );
    if (!res.success || !res.data) {
      throw new Error(res.message || 'Failed to add watchlist entry');
    }
    const created = mapWatchlistFromApi(res.data);
    watchlistStore.update((list) => [created, ...list]);
    return created;
  }

  async update(
    entityType: WatchlistEntityType,
    entityId: string,
    payload: WatchlistUpdatePayload,
  ): Promise<WatchlistEntry> {
    this.error.set(null);
    const url = `${this.baseUrl}/${entityType}/${encodeURIComponent(entityId)}`;

    if (environment.useMock) {
      let updated!: WatchlistEntry;
      watchlistStore.update((list) =>
        list.map((e) => {
          if (e.entityType !== entityType || e.entityId !== entityId) return e;
          updated = {
            ...e,
            ...(payload.watchlist_reason !== undefined ? { reason: payload.watchlist_reason } : {}),
            ...(payload.risk_severity !== undefined ? { severity: payload.risk_severity } : {}),
            ...(payload.is_blacklist !== undefined ? { isBlacklist: payload.is_blacklist } : {}),
            ...(payload.expires_at !== undefined
              ? { expiresAt: payload.expires_at ?? undefined }
              : {}),
          };
          return updated;
        }),
      );
      return updated;
    }

    const res = await firstValueFrom(
      this.http.patch<ApiResponse<WatchlistApiEntry>>(url, payload),
    );
    if (!res.success || !res.data) {
      throw new Error(res.message || 'Failed to update watchlist entry');
    }
    const updated = mapWatchlistFromApi(res.data);
    watchlistStore.update((list) =>
      list.map((e) =>
        e.entityType === entityType && e.entityId === entityId ? updated : e,
      ),
    );
    return updated;
  }

  async remove(entityType: WatchlistEntityType, entityId: string): Promise<void> {
    this.error.set(null);
    const url = `${this.baseUrl}/${entityType}/${encodeURIComponent(entityId)}`;

    if (environment.useMock) {
      watchlistStore.update((list) =>
        list.filter((e) => !(e.entityType === entityType && e.entityId === entityId)),
      );
      return;
    }

    const res = await firstValueFrom(this.http.delete<ApiResponse<null>>(url));
    if (!res.success) {
      throw new Error(res.message || 'Failed to remove watchlist entry');
    }
    watchlistStore.update((list) =>
      list.filter((e) => !(e.entityType === entityType && e.entityId === entityId)),
    );
  }
}
