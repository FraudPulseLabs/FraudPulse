import { DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { WatchlistService } from '../../core/services/watchlist.service';
import type { WatchlistEntityType, WatchlistEntry } from '../../core/models';
import { isWatchlistEntryExpired } from '../../core/models/watchlist.model';
import { BadgeComponent } from '../../shared/components/badge/badge.component';
import { ConfirmDialogComponent } from '../../shared/components/confirm-dialog/confirm-dialog.component';
import { EmptyStateComponent } from '../../shared/components/empty-state/empty-state.component';

type EntityFilter = 'ALL' | WatchlistEntityType;

interface WatchlistForm {
  entityId: string;
  reason: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH';
  isBlacklist: boolean;
  expiresIn: '7' | '14' | '30' | 'NEVER';
}

interface PendingRemove {
  entityType: WatchlistEntityType;
  entityId: string;
}

@Component({
  selector: 'app-watchlist',
  standalone: true,
  imports: [BadgeComponent, ConfirmDialogComponent, DatePipe, EmptyStateComponent],
  template: `
    <div class="page-header">
      <div>
        <h2 class="page-title">Watchlist</h2>
        <p class="text-sm text-slate-500">Merchants requiring extra scrutiny in fraud decisions.</p>
      </div>
      <button type="button" class="btn-primary" (click)="showAddForm.set(true)" [disabled]="loading()">
        Add Merchant
      </button>
    </div>

    @if (error()) {
      <div class="card mb-4 border border-red-200 bg-red-50 text-sm text-red-700">{{ error() }}</div>
    }

    @if (showAddForm()) {
      <div class="card mb-4">
        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          <label>
            <span class="fp-label">Merchant ID</span>
            <input
              #entityInput
              class="fp-input"
              placeholder="MERCHANT_1001"
              [value]="form().entityId"
              (input)="patchForm({ entityId: entityInput.value })"
            />
          </label>
          <label>
            <span class="fp-label">Reason</span>
            <input
              #reasonInput
              class="fp-input"
              [value]="form().reason"
              (input)="patchForm({ reason: reasonInput.value })"
            />
          </label>
          <label>
            <span class="fp-label">Severity</span>
            <select
              #severitySelect
              class="fp-select"
              [value]="form().severity"
              (change)="patchForm({ severity: asSeverity(severitySelect.value) })"
            >
              <option value="LOW">LOW</option>
              <option value="MEDIUM">MEDIUM</option>
              <option value="HIGH">HIGH</option>
            </select>
          </label>
          <label>
            <span class="fp-label">Expires in</span>
            <select
              #expiresSelect
              class="fp-select"
              [value]="form().expiresIn"
              (change)="patchForm({ expiresIn: asExpiry(expiresSelect.value) })"
            >
              <option value="7">7 days</option>
              <option value="14">14 days</option>
              <option value="30">30 days</option>
              <option value="NEVER">Never</option>
            </select>
          </label>
          <label class="flex items-center gap-2 pt-7 text-sm text-slate-700">
            <input
              type="checkbox"
              [checked]="form().isBlacklist"
              (change)="patchForm({ isBlacklist: !form().isBlacklist })"
            />
            Add to blacklist
          </label>
        </div>
        <div class="mt-4 flex flex-wrap items-center gap-3">
          <button type="button" class="btn-primary" (click)="addEntry()">Add to Watchlist</button>
          <button type="button" class="btn-secondary" (click)="cancelAdd()">Cancel</button>
        </div>
      </div>
    }

    <div class="card mb-4">
      <div class="flex flex-wrap items-center gap-3">
        <div class="flex flex-wrap gap-2">
        @for (filter of filters; track filter) {
          <button
            type="button"
            class="px-3 py-1.5 rounded-lg text-sm font-medium border border-slate-200"
            [class.bg-indigo-600]="entityFilter() === filter"
            [class.text-white]="entityFilter() === filter"
            [class.text-slate-600]="entityFilter() !== filter"
            (click)="entityFilter.set(filter)"
          >
            {{ filter }}
          </button>
        }
        </div>
        <label class="ml-auto inline-flex items-center gap-2 text-sm text-slate-600">
          <input
            type="checkbox"
            class="h-4 w-4"
            [checked]="showExpired()"
            (change)="toggleShowExpired($event)"
          />
          Include expired
        </label>
      </div>
    </div>

    <div class="card overflow-hidden">
      @if (loading()) {
        <p class="p-6 text-sm text-slate-500">Loading watchlist…</p>
      } @else if (filtered().length === 0) {
        <app-empty-state message="No watchlist entries found" />
      } @else {
        <div class="overflow-auto">
          <table class="fp-table">
            <thead>
              <tr>
                <th>Type</th>
                <th>Entity ID</th>
                <th>Reason</th>
                <th>Severity</th>
                <th>Blacklist</th>
                <th>Added by</th>
                <th>Expires</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              @for (entry of filtered(); track entry.id) {
                <tr [class.opacity-60]="isWatchlistEntryExpired(entry)">
                  <td><span [class]="typeClass(entry.entityType)">{{ entry.entityType }}</span></td>
                  <td><span class="font-mono">{{ entry.entityId }}</span></td>
                  <td>{{ entry.reason }}</td>
                  <td><app-badge [value]="entry.severity" /></td>
                  <td>
                    @if (entry.isBlacklist) {
                      <span class="badge-block">Blacklisted</span>
                    }
                    @if (isWatchlistEntryExpired(entry)) {
                      <span class="ml-1 rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">Expired</span>
                    }
                  </td>
                  <td>{{ entry.addedBy }}</td>
                  <td>{{ entry.expiresAt ? (entry.expiresAt | date: 'dd MMM yy') : 'Never' }}</td>
                  <td>
                    <button
                      type="button"
                      class="btn-ghost text-red-600"
                      (click)="confirmRemove(entry)"
                      [disabled]="saving()"
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      }
    </div>

    <app-confirm-dialog
      [open]="!!pendingRemove()"
      title="Remove from watchlist"
      [message]="'Remove ' + (pendingRemove()?.entityId ?? '') + ' from the watchlist?'"
      (confirmed)="onRemoveConfirmed($event)"
    />
  `,
})
export class WatchlistComponent implements OnInit {
  private watchlistService = inject(WatchlistService);

  filters: EntityFilter[] = ['ALL', 'MERCHANT'];
  entityFilter = signal<EntityFilter>('ALL');
  showExpired = signal(false);
  showAddForm = signal(false);
  saving = signal(false);
  pendingRemove = signal<PendingRemove | null>(null);
  form = signal<WatchlistForm>({
    entityId: '',
    reason: '',
    severity: 'MEDIUM',
    isBlacklist: false,
    expiresIn: '14',
  });

  readonly loading = this.watchlistService.loading;
  readonly error = this.watchlistService.error;

  filtered = computed(() => {
    let rows = this.watchlistService.entries();
    if (!this.showExpired()) {
      rows = rows.filter((e) => !isWatchlistEntryExpired(e));
    }
    if (this.entityFilter() !== 'ALL') {
      rows = rows.filter((e) => e.entityType === this.entityFilter());
    }
    return rows;
  });

  ngOnInit(): void {
    void this.reloadEntries();
  }

  toggleShowExpired(event: Event): void {
    this.showExpired.set((event.target as HTMLInputElement).checked);
    void this.reloadEntries();
  }

  private reloadEntries(): Promise<void> {
    return this.watchlistService.loadEntries({ includeExpired: this.showExpired() });
  }

  protected readonly isWatchlistEntryExpired = isWatchlistEntryExpired;

  patchForm(patch: Partial<WatchlistForm>): void {
    this.form.update((current) => ({ ...current, ...patch }));
  }

  async addEntry(): Promise<void> {
    const form = this.form();
    if (!form.entityId.trim() || !form.reason.trim()) return;

    const entry: Omit<WatchlistEntry, 'id' | 'createdAt'> = {
      entityType: 'MERCHANT',
      entityId: form.entityId.trim(),
      reason: form.reason.trim(),
      severity: form.severity,
      isBlacklist: form.isBlacklist,
      addedBy: 'fraud_analyst_01',
      ...(form.expiresIn === 'NEVER'
        ? {}
        : { expiresAt: new Date(Date.now() + Number(form.expiresIn) * 86_400_000).toISOString() }),
    };

    this.saving.set(true);
    try {
      await this.watchlistService.add(entry);
      this.cancelAdd();
    } catch {
      // error signal set in service
    } finally {
      this.saving.set(false);
    }
  }

  confirmRemove(entry: WatchlistEntry): void {
    this.pendingRemove.set({ entityType: entry.entityType, entityId: entry.entityId });
  }

  async onRemoveConfirmed(confirmed: boolean): Promise<void> {
    const pending = this.pendingRemove();
    this.pendingRemove.set(null);
    if (!confirmed || !pending) return;

    this.saving.set(true);
    try {
      await this.watchlistService.remove(pending.entityType, pending.entityId);
    } catch {
      // error signal set in service
    } finally {
      this.saving.set(false);
    }
  }

  cancelAdd(): void {
    this.showAddForm.set(false);
    this.form.set({
      entityId: '',
      reason: '',
      severity: 'MEDIUM',
      isBlacklist: false,
      expiresIn: '14',
    });
  }

  asSeverity(value: string): WatchlistForm['severity'] {
    return value as WatchlistForm['severity'];
  }

  asExpiry(value: string): WatchlistForm['expiresIn'] {
    return value as WatchlistForm['expiresIn'];
  }

  typeClass(type: WatchlistEntityType): string {
    const map: Record<WatchlistEntityType, string> = {
      USER: 'inline-flex rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-medium text-indigo-700',
      MERCHANT: 'inline-flex rounded-full bg-yellow-50 px-2.5 py-0.5 text-xs font-medium text-yellow-700',
      TRANSACTION: 'inline-flex rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700',
    };
    return map[type];
  }
}
