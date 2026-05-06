import { Component, computed, inject, signal } from '@angular/core';
import { AlertService } from '../../../core/services/alert.service';
import type { AlertStatus } from '../../../core/models';
import { BadgeComponent } from '../../../shared/components/badge/badge.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { TimeAgoPipe } from '../../../shared/pipes/time-ago.pipe';

type StatusFilter = 'ALL' | AlertStatus;

@Component({
  selector: 'app-alert-queue',
  standalone: true,
  imports: [BadgeComponent, EmptyStateComponent, TimeAgoPipe],
  template: `
    <div class="page-header">
      <div>
        <h2 class="page-title">Alert Queue</h2>
        <p class="text-sm text-slate-500">Prioritised alert triage for review and resolution.</p>
      </div>
    </div>

    <div class="card mb-4">
      <div class="flex flex-wrap items-center justify-between gap-4">
        <div class="inline-flex rounded-lg border border-slate-200 bg-white p-1">
          @for (status of statuses; track status) {
            <button
              type="button"
              class="px-3 py-1.5 rounded-lg text-sm font-medium"
              [class.bg-indigo-600]="statusFilter() === status"
              [class.text-white]="statusFilter() === status"
              [class.text-slate-600]="statusFilter() !== status"
              (click)="statusFilter.set(status)"
            >
              {{ status }}
            </button>
          }
        </div>
        <div class="flex items-center gap-3 text-sm">
          <span class="text-red-700 font-medium">{{ newCounts().HIGH }} HIGH</span>
          <span class="text-yellow-700 font-medium">{{ newCounts().MEDIUM }} MEDIUM</span>
          <span class="text-blue-700 font-medium">{{ newCounts().LOW }} LOW</span>
        </div>
      </div>
    </div>

    <div class="card overflow-hidden">
      @if (filtered().length === 0) {
        <app-empty-state icon="Done" message="No alerts in this queue" />
      } @else {
        <div class="overflow-auto">
          <table class="fp-table">
            <thead>
              <tr>
                <th>Age</th>
                <th>Alert ID</th>
                <th>Transaction</th>
                <th>Reason</th>
                <th>Severity</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              @for (alert of filtered(); track alert.id) {
                <tr>
                  <td>{{ alert.createdAt | timeAgo }}</td>
                  <td><span class="font-mono">{{ alert.id }}</span></td>
                  <td><span class="font-mono">{{ alert.transactionId }}</span></td>
                  <td class="max-w-md">{{ alert.reason }}</td>
                  <td><app-badge [value]="alert.severity" /></td>
                  <td><app-badge [value]="alert.status" /></td>
                  <td>
                    <div class="flex items-center gap-2">
                      @if (alert.status === 'NEW') {
                        <button type="button" class="btn-secondary" (click)="acknowledge(alert.id)">Acknowledge</button>
                        <button type="button" class="btn-ghost" (click)="startResolve(alert.id)">Resolve</button>
                      } @else if (alert.status === 'ACKNOWLEDGED') {
                        <button type="button" class="btn-secondary" (click)="startResolve(alert.id)">Resolve</button>
                      } @else {
                        <span class="text-sm text-slate-400">Done</span>
                      }
                    </div>
                  </td>
                </tr>
                @if (resolvingId() === alert.id) {
                  <tr>
                    <td colspan="7">
                      <div class="flex items-center gap-3">
                        <input
                          #noteInput
                          class="fp-input"
                          placeholder="Resolution note..."
                          [value]="resolveNote()"
                          (input)="resolveNote.set(noteInput.value)"
                        />
                        <button type="button" class="btn-primary" (click)="resolveAlert(alert.id, resolveNote())">Confirm</button>
                        <button type="button" class="btn-secondary" (click)="cancelResolve()">Cancel</button>
                      </div>
                    </td>
                  </tr>
                }
              }
            </tbody>
          </table>
        </div>
      }
    </div>
  `,
})
export class AlertQueueComponent {
  private alertService = inject(AlertService);

  statuses: StatusFilter[] = ['ALL', 'NEW', 'ACKNOWLEDGED', 'RESOLVED'];
  statusFilter = signal<StatusFilter>('NEW');
  resolvingId = signal<string | null>(null);
  resolveNote = signal('');

  filtered = computed(() =>
    this.statusFilter() === 'ALL'
      ? this.alertService.byStatus()
      : this.alertService.byStatus(this.statusFilter() as AlertStatus),
  );

  newCounts = computed(() => {
    const open = this.alertService.byStatus('NEW');
    return {
      HIGH: open.filter((a) => a.severity === 'HIGH').length,
      MEDIUM: open.filter((a) => a.severity === 'MEDIUM').length,
      LOW: open.filter((a) => a.severity === 'LOW').length,
    };
  });

  acknowledge(id: string): void {
    // TODO: optimistic update + API call
    this.alertService.acknowledge(id);
  }

  startResolve(id: string): void {
    this.resolvingId.set(id);
    this.resolveNote.set('');
  }

  resolveAlert(id: string, note: string): void {
    if (!note.trim()) return;
    // TODO: POST /alerts/:id/resolve
    this.alertService.resolve(id, note);
    this.resolvingId.set(null);
    this.resolveNote.set('');
  }

  createCaseFromAlert(alertId: string): void {
    // TODO: open create-case dialog with this alert pre-selected
    console.warn('[TODO] open create case dialog for alert', alertId);
  }

  cancelResolve(): void {
    this.resolvingId.set(null);
    this.resolveNote.set('');
  }
}
