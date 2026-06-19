import { signal } from '@angular/core';
import type { WatchlistEntry } from '../models';

/** In-memory cache populated by WatchlistService from the API. */
export const watchlistStore = signal<WatchlistEntry[]>([]);
