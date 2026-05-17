import { DatePipe, DecimalPipe } from '@angular/common';
import { Component, computed, inject, input, signal } from '@angular/core';
import { AlertService } from '../../../core/services/alert.service';
import { CaseService } from '../../../core/services/case.service';
import { TransactionService } from '../../../core/services/transaction.service';
import type { CaseEventType, CaseStatus, ResolutionCode } from '../../../core/models';
import { BadgeComponent } from '../../../shared/components/badge/badge.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { ScoreBarComponent } from '../../../shared/components/score-bar/score-bar.component';
import { TimeAgoPipe } from '../../../shared/pipes/time-ago.pipe';

@Component({
  selector: 'app-case-detail',
  standalone: true,
  imports: [BadgeComponent, DatePipe, DecimalPipe, EmptyStateComponent, ScoreBarComponent, TimeAgoPipe],
  template: `
    @if (c(); as current) {
      <div class="grid grid-cols-1 xl:grid-cols-[minmax(0,3fr)_minmax(320px,2fr)] gap-6">
        <div class="space-y-6">
          <section class="card">
            <div class="flex items-start justify-between gap-4">
              <div>
                <h2 class="text-xl font-semibold text-slate-900">{{ current.title }}</h2>
                <p class="text-sm text-slate-500">
                  <span class="font-mono">{{ current.id }}</span> - created {{ current.createdAt | date: 'mediumDate' }}
                </p>
              </div>
              <div class="flex items-center gap-2">
                <app-badge [value]="current.status" />
                <app-badge [value]="current.riskLevel" />
              </div>
            </div>

            <div class="mt-6">
              <h3 class="section-title">Status control</h3>
              <div class="flex flex-wrap items-center gap-2">
                @for (status of statuses; track status) {
                  <button
                    type="button"
                    class="px-3 py-1.5 rounded-lg text-sm font-medium border border-slate-200"
                    [class.bg-indigo-600]="pendingStatus() === status"
                    [class.text-white]="pendingStatus() === status"
                    [class.text-slate-600]="pendingStatus() !== status"
                    (click)="pendingStatus.set(status)"
                  >
                    {{ status }}
                  </button>
                }
                @if (pendingStatus() === 'CLOSED') {
                  <select #resolutionSelect class="fp-select w-56" [value]="pendingResolution() || ''" (change)="setResolution(resolutionSelect.value)">
                    <option value="">Resolution</option>
                    <option value="CONFIRMED_FRAUD">CONFIRMED_FRAUD</option>
                    <option value="FALSE_POSITIVE">FALSE_POSITIVE</option>
                    <option value="INCONCLUSIVE">INCONCLUSIVE</option>
                  </select>
                }
                <button type="button" class="btn-primary" (click)="updateStatus()">Apply</button>
                <button type="button" class="btn-secondary" (click)="assignCase('analyst@fraudpulse.demo')">Assign</button>
              </div>
            </div>
          </section>

          <section class="card">
            <h3 class="section-title">Linked Transactions</h3>
            <div class="overflow-auto">
              <table class="fp-table">
                <thead>
                  <tr><th>TX ID</th><th>Amount</th><th>Score</th><th>Decision</th><th>Lifecycle</th></tr>
                </thead>
                <tbody>
                  @for (tx of linkedTransactions(); track tx.id) {
                    <tr>
                      <td><span class="font-mono">{{ tx.id }}</span></td>
                      <td>KES {{ tx.amount | number: '1.0-0' }}</td>
                      <td><app-score-bar [score]="tx.score" /></td>
                      <td><app-badge [value]="tx.decision" /></td>
                      <td><app-badge [value]="tx.lifecycleStatus" /></td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          </section>

          <section class="card">
            <h3 class="section-title">Linked Alerts</h3>
            <div class="space-y-2">
              @for (alert of linkedAlerts(); track alert.id) {
                <div class="flex items-center justify-between gap-4 rounded-lg border border-slate-200 p-3">
                  <div>
                    <p class="font-mono text-sm text-slate-700">{{ alert.id }}</p>
                    <p class="text-sm text-slate-500">{{ alert.reason }}</p>
                  </div>
                  <div class="flex items-center gap-2">
                    <app-badge [value]="alert.severity" />
                    <app-badge [value]="alert.status" />
                  </div>
                </div>
              }
            </div>
          </section>
        </div>

        <div class="space-y-6">
          <section class="card">
            <h3 class="section-title">Timeline</h3>
            <div class="space-y-4">
              @for (event of timeline(); track event.timestamp + event.description) {
                <div class="flex gap-3">
                  <span class="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-sm">{{ iconFor(event.type) }}</span>
                  <div>
                    <p class="text-sm font-medium text-slate-700">{{ event.description }}</p>
                    <p class="text-xs text-slate-400">{{ event.actor }} - {{ event.timestamp | timeAgo }}</p>
                  </div>
                </div>
              }
            </div>
          </section>

          <section class="card">
            <h3 class="section-title">Notes</h3>
            <div class="space-y-3">
              @for (note of notes(); track note.timestamp + note.body) {
                <article class="rounded-lg bg-slate-50 p-3">
                  <div class="flex items-center justify-between gap-2">
                    <span class="text-xs font-medium text-slate-700">{{ note.author }}</span>
                    <span class="text-xs text-slate-400">{{ note.timestamp | timeAgo }}</span>
                  </div>
                  <p class="mt-2 text-sm text-slate-600">{{ note.body }}</p>
                </article>
              }
            </div>
            <div class="mt-4">
              <textarea #noteInput class="fp-input min-h-28" rows="4" [value]="noteBody()" (input)="noteBody.set(noteInput.value)"></textarea>
              <div class="mt-2 flex items-center justify-between">
                <span class="text-xs text-slate-400">{{ noteBody().length }} / 2000</span>
                <button type="button" class="btn-primary" (click)="submitNote()">Add Note</button>
              </div>
            </div>
          </section>
        </div>
      </div>
    } @else {
      <app-empty-state message="Case not found" />
    }
  `,
})
export class CaseDetailComponent {
  private caseService = inject(CaseService);
  private alertService = inject(AlertService);
  private txService = inject(TransactionService);

  id = input.required<string>();
  statuses: CaseStatus[] = ['OPEN', 'INVESTIGATING', 'CLOSED'];
  pendingStatus = signal<CaseStatus | null>(null);
  pendingResolution = signal<ResolutionCode | null>(null);
  noteBody = signal('');

  c = computed(() => this.caseService.getById(this.id()));
  linkedTransactions = computed(() => {
    const current = this.c();
    return current ? current.linkedTransactionIds.map((id) => this.txService.getById(id)).filter((tx) => tx != null) : [];
  });
  linkedAlerts = computed(() => {
    const current = this.c();
    return current ? current.linkedAlertIds.map((id) => this.alertService.getById(id)).filter((alert) => alert != null) : [];
  });
  timeline = computed(() => [...(this.c()?.timeline ?? [])].sort((a, b) => b.timestamp.localeCompare(a.timestamp)));
  notes = computed(() => [...(this.c()?.notes ?? [])].sort((a, b) => b.timestamp.localeCompare(a.timestamp)));

  setResolution(value: string): void {
    this.pendingResolution.set(value ? (value as ResolutionCode) : null);
  }

  updateStatus(): void {
    const status = this.pendingStatus();
    if (!status) return;
    // TODO: validation - CLOSED requires resolutionCode
    this.caseService.updateStatus(this.id(), status, this.pendingResolution() ?? undefined);
    this.pendingStatus.set(null);
  }

  submitNote(): void {
    const body = this.noteBody().trim();
    if (!body || body.length > 2000) return;
    // TODO: POST /cases/:id/notes
    this.caseService.addNote(this.id(), body);
    this.noteBody.set('');
  }

  assignCase(analyst: string): void {
    // TODO: open analyst picker dialog
    console.warn('[TODO] assign case to analyst', analyst);
    this.caseService.assign(this.id(), analyst);
  }

  iconFor(type: CaseEventType): string {
    const map: Record<CaseEventType, string> = {
      ALERT_ADDED: 'A',
      STATUS_CHANGED: 'S',
      NOTE_ADDED: 'N',
      ASSIGNMENT_CHANGED: 'U',
      RULE_TRIGGER: 'R',
    };
    return map[type];
  }
}
