import { DatePipe } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { WatchlistService } from '../../core/services/watchlist.service';
import type { WatchlistEntityType, WatchlistEntry } from '../../core/models';
import { BadgeComponent } from '../../shared/components/badge/badge.component';
import { EmptyStateComponent } from '../../shared/components/empty-state/empty-state.component';

type EntityFilter = 'ALL' | WatchlistEntityType;

interface WatchlistForm {
  entityType: WatchlistEntityType;
  entityId: string;
  reason: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH';
  isBlacklist: boolean;
  expiresIn: '7' | '14' | '30' | 'NEVER';
}

@Component({
  selector: 'app-watchlist',
  standalone: true,
  imports: [BadgeComponent, DatePipe, EmptyStateComponent],
  template: `
    <div class="page-header">
      <div>
        <h2 class="page-title">Watchlist</h2>
        <p class="text-sm text-slate-500">Entities requiring extra scrutiny in fraud decisions.</p>
      </div>
      <button type="button" class="btn-primary" (click)="showAddForm.set(true)">Add Entry</button>
    </div>

    @if (showAddForm()) {
      <div class="card mb-4">
        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          <label>
            <span class="fp-label">Entity Type</span>
            <select #typeSelect class="fp-select" [value]="form().entityType" (change)="patchForm({ entityType: asEntityType(typeSelect.value) })">
              <option value="USER">USER</option>
              <option value="MERCHANT">MERCHANT</option>
              <option value="TRANSACTION">TRANSACTION</option>
            </select>
          </label>
          <label>
            <span class="fp-label">Entity ID</span>
            <input #entityInput class="fp-input" placeholder="USR-007 or merchant name" [value]="form().entityId" (input)="patchForm({ entityId: entityInput.value })" />
          </label>
          <label>
            <span class="fp-label">Reason</span>
            <input #reasonInput class="fp-input" [value]="form().reason" (input)="patchForm({ reason: reasonInput.value })" />
          </label>
          <label>
            <span class="fp-label">Severity</span>
            <select #severitySelect class="fp-select" [value]="form().severity" (change)="patchForm({ severity: asSeverity(severitySelect.value) })">
              <option value="LOW">LOW</option>
              <option value="MEDIUM">MEDIUM</option>
              <option value="HIGH">HIGH</option>
            </select>
          </label>
          <label>
            <span class="fp-label">Expires in</span>
            <select #expiresSelect class="fp-select" [value]="form().expiresIn" (change)="patchForm({ expiresIn: asExpiry(expiresSelect.value) })">
              <option value="7">7 days</option>
              <option value="14">14 days</option>
              <option value="30">30 days</option>
              <option value="NEVER">Never</option>
            </select>
          </label>
          <label class="flex items-center gap-2 pt-7 text-sm text-slate-700">
            <input type="checkbox" [checked]="form().isBlacklist" (change)="patchForm({ isBlacklist: !form().isBlacklist })" />
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
    </div>

    <div class="card overflow-hidden">
      @if (filtered().length === 0) {
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
                <tr>
                  <td><span [class]="typeClass(entry.entityType)">{{ entry.entityType }}</span></td>
                  <td><span class="font-mono">{{ entry.entityId }}</span></td>
                  <td>{{ entry.reason }}</td>
                  <td><app-badge [value]="entry.severity" /></td>
                  <td>
                    @if (entry.isBlacklist) {
                      <span class="badge-block">Blacklisted</span>
                    }
                  </td>
                  <td>{{ entry.addedBy }}</td>
                  <td>{{ entry.expiresAt ? (entry.expiresAt | date: 'dd MMM yy') : 'Never' }}</td>
                  <td>
                    <button type="button" class="btn-ghost text-red-600" (click)="removeEntry(entry.id, entry.entityId)">Remove</button>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      }
    </div>
  `,
})
export class WatchlistComponent {
  private watchlistService = inject(WatchlistService);

  filters: EntityFilter[] = ['ALL', 'USER', 'MERCHANT', 'TRANSACTION'];
  entityFilter = signal<EntityFilter>('ALL');
  showAddForm = signal(false);
  form = signal<WatchlistForm>({
    entityType: 'USER',
    entityId: '',
    reason: '',
    severity: 'MEDIUM',
    isBlacklist: false,
    expiresIn: '14',
  });

  filtered = computed(() =>
    this.entityFilter() === 'ALL'
      ? this.watchlistService.entries()
      : this.watchlistService.entries().filter((e) => e.entityType === this.entityFilter()),
  );

  patchForm(patch: Partial<WatchlistForm>): void {
    this.form.update((current) => ({ ...current, ...patch }));
  }

  addEntry(): void {
    // TODO: validate all required fields
    // TODO: POST /watchlist { ...form }
    const form = this.form();
    if (!form.entityId.trim() || !form.reason.trim()) return;
    const entry: Omit<WatchlistEntry, 'id' | 'createdAt'> = {
      entityType: form.entityType,
      entityId: form.entityId,
      reason: form.reason,
      severity: form.severity,
      isBlacklist: form.isBlacklist,
      addedBy: 'analyst@fraudpulse.demo',
      ...(form.expiresIn === 'NEVER'
        ? {}
        : { expiresAt: new Date(Date.now() + Number(form.expiresIn) * 86_400_000).toISOString() }),
    };
    this.watchlistService.add(entry);
    this.cancelAdd();
  }

  removeEntry(id: string, entityId: string): void {
    // TODO: confirm dialog
    // TODO: DELETE /watchlist/:id
    console.warn('[TODO] remove watchlist entry', entityId);
    this.watchlistService.remove(id);
  }

  cancelAdd(): void {
    this.showAddForm.set(false);
    this.form.set({
      entityType: 'USER',
      entityId: '',
      reason: '',
      severity: 'MEDIUM',
      isBlacklist: false,
      expiresIn: '14',
    });
  }

  asEntityType(value: string): WatchlistEntityType {
    return value as WatchlistEntityType;
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
