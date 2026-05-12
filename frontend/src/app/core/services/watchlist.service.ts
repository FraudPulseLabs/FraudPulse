import { Injectable } from '@angular/core';
import { watchlistStore } from '../mock/watchlist.mock';
import type { WatchlistEntry, WatchlistEntityType } from '../models';

@Injectable({ providedIn: 'root' })
export class WatchlistService {
  readonly entries = watchlistStore.asReadonly();

  isWatchlisted(entityType: WatchlistEntityType, entityId: string): boolean {
    return watchlistStore().some((e) => e.entityType === entityType && e.entityId === entityId);
  }

  add(entry: Omit<WatchlistEntry, 'id' | 'createdAt'>): void {
    // TODO: POST /watchlist { ...entry }
    console.warn('[TODO] add to watchlist', entry.entityId);
    const newEntry: WatchlistEntry = {
      ...entry,
      id: `WL-${Date.now()}`,
      createdAt: new Date().toISOString(),
    };
    watchlistStore.update((list) => [newEntry, ...list]);
  }

  remove(id: string): void {
    // TODO: DELETE /watchlist/:id
    console.warn('[TODO] remove from watchlist', id);
    watchlistStore.update((list) => list.filter((e) => e.id !== id));
  }
}
