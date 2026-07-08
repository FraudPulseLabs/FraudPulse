import { signal } from '@angular/core';
import type { Transaction } from '../models';

/** In-memory cache populated by TransactionService from the API. */
export const txStore = signal<Transaction[]>([]);
