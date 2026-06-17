//frontend\src\app\features\cases\case-detail\case-detail.component.ts
import { DatePipe, DecimalPipe } from '@angular/common';
import { Component, computed, inject, input, signal, OnInit } from '@angular/core';
import { AlertService } from '../../../core/services/alert.service';
import { CaseService } from '../../../core/services/case.service';
import { ProfileService } from '../../../core/services/profile.service';
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

          <!-- Header -->
          <section class="card">
            <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div class="min-w-0">
                <h2 class="text-xl font-semibold text-slate-900">{{ current.title }}</h2>
                <p class="text-sm text-slate-500 mt-1">
                  <span class="font-mono">{{ current.id }}</span> &middot;
                  created {{ current.createdAt | date: 'mediumDate' }}
                  @if (current.assignedTo) {
                    &middot; assigned to
                    <span class="font-medium text-slate-700">{{ assignedName() }}</span>
                  }
                </p>
              </div>
              <div class="flex flex-wrap items-center gap-2">
                <app-badge [value]="current.status" />
                <app-badge [value]="current.riskLevel" />
                @if (current.resolutionCode) {
                  <app-badge [value]="current.resolutionCode" />
                }
              </div>
            </div>

            <!-- Status control -->
            <div class="mt-6 space-y-4">
              <div>
                <h3 class="section-title">Update status</h3>
                <div class="flex flex-wrap items-center gap-2">
                  @for (status of statuses; track status) {
                    <button
                      type="button"
                      class="px-3 py-1.5 rounded-lg text-sm font-medium border border-slate-200"
                      [class.bg-indigo-600]="pendingStatus() === status"
                      [class.text-white]="pendingStatus() === status"
                      [class.text-slate-600]="pendingStatus() !== status"
                      (click)="pendingStatus.set(status)"
                    >{{ status }}</button>
                  }
                  @if (pendingStatus() === 'CLOSED') {
                    <select #resolutionSelect class="fp-select w-full sm:w-56"
                      [value]="pendingResolution() || ''"
                      (change)="setResolution(resolutionSelect.value)">
                      <option value="">Select resolution…</option>
                      <option value="CONFIRMED_FRAUD">CONFIRMED_FRAUD</option>
                      <option value="FALSE_POSITIVE">FALSE_POSITIVE</option>
                      <option value="INCONCLUSIVE">INCONCLUSIVE</option>
                    </select>
                  }
                  <button type="button" class="btn-primary" (click)="updateStatus()">Apply</button>
                </div>
              </div>

              <!-- Analyst assignment -->
              <div>
                <h3 class="section-title">Assign to analyst</h3>
                @if (showAssignPicker()) {
                  <div class="flex flex-wrap items-center gap-2">
                    <select #analystSelect class="fp-select w-full sm:w-72"
                      [value]="pendingAnalyst() || ''"
                      (change)="pendingAnalyst.set(analystSelect.value)">
                      <option value="">Select analyst…</option>
                      @for (analyst of analysts(); track analyst.id) {
                        <option [value]="analyst.id">{{ analyst.fullName }}</option>
                      }
                    </select>
                    <button type="button" class="btn-primary" (click)="confirmAssign()">Assign</button>
                    <button type="button" class="btn-secondary" (click)="showAssignPicker.set(false)">Cancel</button>
                  </div>
                } @else {
                  <button type="button" class="btn-secondary" (click)="openAssignPicker()">
                    {{ current.assignedTo ? 'Reassign' : 'Assign analyst' }}
                  </button>
                }
              </div>
            </div>
          </section>

          <!-- Transaction details -->
          <section class="card">
            <h3 class="section-title">Transaction</h3>
            @if (transaction(); as tx) {
              <div class="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-3 text-sm">
                <div>
                  <p class="text-xs text-slate-400 uppercase tracking-wide">Amount</p>
                  <p class="font-medium text-slate-800">
                    {{ tx.transactionCurrency }} {{ tx.transactionAmount | number: '1.2-2' }}
                  </p>
                </div>
                <div>
                  <p class="text-xs text-slate-400 uppercase tracking-wide">USD Equiv.</p>
                  <p class="font-medium text-slate-800">
                    {{ tx.enrichedAmountUsd !== null ? ('$' + (tx.enrichedAmountUsd | number: '1.2-2')) : '—' }}
                  </p>
                </div>
                <div>
                  <p class="text-xs text-slate-400 uppercase tracking-wide">Decision</p>
                  <app-badge [value]="tx.decision ?? 'UNKNOWN'" />
                </div>
                <div>
                  <p class="text-xs text-slate-400 uppercase tracking-wide">Fraud Score</p>
                  @if (tx.fraudScore !== null) {
                    <app-score-bar [score]="tx.fraudScore" />
                  } @else {
                    <p class="text-slate-500">—</p>
                  }
                </div>
                <div>
                  <p class="text-xs text-slate-400 uppercase tracking-wide">Channel</p>
                  <p class="font-medium text-slate-800">{{ tx.channel ?? '—' }}</p>
                </div>
                <div>
                  <p class="text-xs text-slate-400 uppercase tracking-wide">Card Type</p>
                  <p class="font-medium text-slate-800">{{ tx.cardType ?? '—' }}</p>
                </div>
                <div>
                  <p class="text-xs text-slate-400 uppercase tracking-wide">Merchant</p>
                  <p class="font-mono text-xs text-slate-700 truncate">{{ tx.merchantId }}</p>
                </div>
                <div>
                  <p class="text-xs text-slate-400 uppercase tracking-wide">MCC</p>
                  <p class="font-medium text-slate-800">{{ tx.merchantCategoryCode ?? '—' }}</p>
                </div>
                <div>
                  <p class="text-xs text-slate-400 uppercase tracking-wide">Country</p>
                  <p class="font-medium text-slate-800">{{ tx.transactionCountry ?? '—' }}</p>
                </div>
                <div>
                  <p class="text-xs text-slate-400 uppercase tracking-wide">Auth Method</p>
                  <p class="font-medium text-slate-800">{{ tx.authentication ?? '—' }}</p>
                </div>
                <div>
                  <p class="text-xs text-slate-400 uppercase tracking-wide">Entry Mode</p>
                  <p class="font-medium text-slate-800">{{ tx.panEntryMode ?? '—' }}</p>
                </div>
                <div>
                  <p class="text-xs text-slate-400 uppercase tracking-wide">Timestamp</p>
                  <p class="font-medium text-slate-800">{{ tx.ts | date: 'medium' }}</p>
                </div>
                @if (tx.reasonCode) {
                  <div class="col-span-2 sm:col-span-3">
                    <p class="text-xs text-slate-400 uppercase tracking-wide">Reason Code</p>
                    <p class="font-medium text-red-700">{{ tx.reasonCode }}</p>
                  </div>
                }
                @if (tx.modelVersion) {
                  <div class="col-span-2 sm:col-span-3">
                    <p class="text-xs text-slate-400 uppercase tracking-wide">Model</p>
                    <p class="font-mono text-xs text-slate-500">{{ tx.modelVersion }}</p>
                  </div>
                }
              </div>
            } @else {
              <p class="text-sm text-slate-400">Loading transaction details…</p>
            }
          </section>

          <!-- Linked alert -->
          <section class="card">
            <h3 class="section-title">Linked Alert</h3>
            @if (linkedAlert(); as alert) {
              <div class="flex flex-col gap-3 rounded-lg border border-slate-200 p-3 sm:flex-row sm:items-center sm:justify-between">
                <div class="min-w-0">
                  <p class="font-mono text-sm text-slate-700">{{ alert.id }}</p>
                  <p class="text-sm text-slate-500">{{ alert.reason }}</p>
                </div>
                <app-badge [value]="alert.severity" />
              </div>
            } @else {
              <p class="text-sm text-slate-400">No linked alert found.</p>
            }
          </section>

        </div>

        <!-- Right column -->
        <div class="space-y-6">

          <!-- Timeline -->
          <section class="card">
            <h3 class="section-title">Timeline</h3>
            @if (events().length === 0) {
              <p class="text-sm text-slate-400">No events yet.</p>
            }
            <div class="space-y-4">
              @for (event of events(); track event.id) {
                <div class="flex gap-3">
                  <span class="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-sm shrink-0">
                    {{ iconFor(event.eventType) }}
                  </span>
                  <div class="min-w-0">
                    <p class="text-sm font-medium text-slate-700">{{ event.description }}</p>
                    <p class="text-xs text-slate-400">{{ event.actor }} &middot; {{ event.createdAt | timeAgo }}</p>
                  </div>
                </div>
              }
            </div>
          </section>

          <!-- Notes -->
          <section class="card">
            <h3 class="section-title">Notes</h3>
            <div class="space-y-3">
              @for (note of notes(); track note.id) {
                <article class="rounded-lg bg-slate-50 p-3">
                  <div class="flex items-center justify-between gap-2">
                    <span class="text-xs font-medium text-slate-700">{{ note.authorId }}</span>
                    <span class="text-xs text-slate-400">{{ note.createdAt | timeAgo }}</span>
                  </div>
                  <p class="mt-2 text-sm text-slate-600">{{ note.body }}</p>
                </article>
              }
              @if (notes().length === 0) {
                <p class="text-sm text-slate-400">No notes yet.</p>
              }
            </div>
            <div class="mt-4">
              <textarea
                #noteInput
                class="fp-input min-h-28"
                rows="4"
                placeholder="Add a note…"
                [value]="noteBody()"
                (input)="noteBody.set(noteInput.value)"
              ></textarea>
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
export class CaseDetailComponent implements OnInit {
  private caseService    = inject(CaseService);
  private alertService   = inject(AlertService);
  private profileService = inject(ProfileService);

  id = input.required<string>();

  statuses: CaseStatus[]   = ['OPEN', 'INVESTIGATING', 'CLOSED'];
  pendingStatus            = signal<CaseStatus | null>(null);
  pendingResolution        = signal<ResolutionCode | null>(null);
  noteBody                 = signal('');
  showAssignPicker         = signal(false);
  pendingAnalyst           = signal<string>('');

  c           = computed(() => this.caseService.getById(this.id()));
  notes       = computed(() => this.caseService.notesForCase(this.id()));
  events      = computed(() => this.caseService.eventsForCase(this.id()));
  analysts    = this.profileService.analysts;

  transaction = computed(() => {
    const current = this.c();
    return current ? this.caseService.transactionFor(current.transactionId) : null;
  });

  linkedAlert = computed(() => {
    const current = this.c();
    if (!current) return undefined;
    return this.alertService.alerts().find(a => a.transactionId === current.transactionId);
  });

  // Resolve the assigned analyst name from the loaded analysts list
  assignedName = computed(() => {
    const current = this.c();
    if (!current?.assignedTo) return null;
    return this.analysts().find(a => a.id === current.assignedTo)?.fullName ?? current.assignedTo;
  });

  ngOnInit(): void {
    this.caseService.load();
    this.caseService.loadNotes(this.id());
    this.caseService.loadEvents(this.id());
    this.alertService.load();
    this.profileService.loadAnalysts();

    // Load transaction once the case signal resolves
    const current = this.c();
    if (current) {
      this.caseService.loadTransaction(current.transactionId);
    }
  }

  ngOnChanges(): void {
    const current = this.c();
    if (current) {
      this.caseService.loadTransaction(current.transactionId);
    }
  }

  setResolution(value: string): void {
    this.pendingResolution.set(value ? (value as ResolutionCode) : null);
  }

  updateStatus(): void {
    const status = this.pendingStatus();
    if (!status) return;
    if (status === 'CLOSED' && !this.pendingResolution()) return; // require resolution
    this.caseService.updateStatus(this.id(), status, this.pendingResolution() ?? undefined);
    this.pendingStatus.set(null);
    this.pendingResolution.set(null);
  }

  openAssignPicker(): void {
    this.pendingAnalyst.set(this.c()?.assignedTo ?? '');
    this.showAssignPicker.set(true);
  }

  confirmAssign(): void {
    const analystId = this.pendingAnalyst();
    if (!analystId) return;
    this.caseService.assign(this.id(), analystId);
    this.showAssignPicker.set(false);
  }

  submitNote(): void {
    const body = this.noteBody().trim();
    if (!body || body.length > 2000) return;
    this.caseService.addNote(this.id(), body, 'analyst@fraudpulse.demo');
    this.noteBody.set('');
  }

  iconFor(type: CaseEventType): string {
    const map: Record<CaseEventType, string> = {
      ALERT_ADDED:        '🚨',
      STATUS_CHANGED:     '🔄',
      NOTE_ADDED:         '📝',
      ASSIGNMENT_CHANGED: '👤',
      RULE_TRIGGER:       '⚡',
    };
    return map[type] ?? '•';
  }
}