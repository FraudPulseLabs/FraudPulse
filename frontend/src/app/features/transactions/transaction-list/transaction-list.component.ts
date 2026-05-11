import { DatePipe, DecimalPipe } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { TransactionService } from '../../../core/services/transaction.service';
import type { Transaction } from '../../../core/models';
import { BadgeComponent } from '../../../shared/components/badge/badge.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { ScoreBarComponent } from '../../../shared/components/score-bar/score-bar.component';

type DecisionFilter = 'ALL' | 'ALLOW' | 'REVIEW' | 'BLOCK';
type ScoreFilter = 'ANY' | 'LOW' | 'MEDIUM' | 'HIGH';

@Component({
  selector: 'app-transaction-list',
  standalone: true,
  imports: [BadgeComponent, DatePipe, DecimalPipe, EmptyStateComponent, RouterLink, ScoreBarComponent],
  template: `
    <div class="page-header">
      <div>
        <h2 class="page-title">Transaction Monitor</h2>
        <p class="text-sm text-slate-500">Live fraud scoring decisions from the mock stream.</p>
      </div>
      <button type="button" class="btn-ghost" (click)="rescoreSelected()">Rescore selected</button>
    </div>

    <div class="card mb-4">
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
        <label>
          <span class="fp-label">Decision</span>
          <select #decisionSelect class="fp-select" [value]="decisionFilter()" (change)="setDecision(decisionSelect.value)">
            <option value="ALL">ALL</option>
            <option value="ALLOW">ALLOW</option>
            <option value="REVIEW">REVIEW</option>
            <option value="BLOCK">BLOCK</option>
          </select>
        </label>
        <label>
          <span class="fp-label">User ID</span>
          <input
            #userInput
            class="fp-input"
            placeholder="USR-007"
            [value]="userIdFilter()"
            (input)="setUserId(userInput.value)"
          />
        </label>
        <label>
          <span class="fp-label">Score</span>
          <select #scoreSelect class="fp-select" [value]="scoreFilter()" (change)="setScore(scoreSelect.value)">
            <option value="ANY">ANY</option>
            <option value="LOW">Under 0.40</option>
            <option value="MEDIUM">0.40-0.79</option>
            <option value="HIGH">0.80+</option>
          </select>
        </label>
        <button type="button" class="btn-ghost justify-center" (click)="resetFilters()">Reset</button>
      </div>
    </div>

    <div class="card overflow-hidden">
      @if (filtered().length === 0) {
        <app-empty-state message="No transactions match these filters" />
      } @else {
        <div class="overflow-auto">
          <table class="fp-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>TX ID</th>
                <th>User</th>
                <th>Merchant</th>
                <th>Amount</th>
                <th>Score</th>
                <th>Decision</th>
                <th>Status</th>
                <th>Info</th>
              </tr>
            </thead>
            <tbody>
              @for (tx of paginated(); track tx.id) {
                <tr>
                  <td>{{ tx.ts | date: 'dd MMM, HH:mm' }}</td>
                  <td><span class="font-mono" [title]="tx.id">{{ tx.id }}</span></td>
                  <td>{{ tx.userId }}</td>
                  <td>{{ tx.merchant }}</td>
                  <td>KES {{ tx.amount | number: '1.0-0' }}</td>
                  <td><app-score-bar [score]="tx.score" /></td>
                  <td><app-badge [value]="tx.decision" /></td>
                  <td><app-badge [value]="tx.lifecycleStatus" /></td>
                  <td>
                    <button type="button" class="btn-ghost" (click)="selectedTx.set(tx)">Open</button>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>

        <div class="mt-4 flex items-center justify-between text-sm text-slate-500">
          <span>Showing {{ rangeStart() }}-{{ rangeEnd() }} of {{ filtered().length }} results</span>
          <div class="flex items-center gap-2">
            <button type="button" class="btn-secondary" [disabled]="page() === 1" (click)="page.set(page() - 1)">Previous</button>
            <span class="text-xs">Page {{ page() }} / {{ totalPages() }}</span>
            <button type="button" class="btn-secondary" [disabled]="page() === totalPages()" (click)="page.set(page() + 1)">Next</button>
          </div>
        </div>
      }
    </div>

    @if (selectedTx(); as tx) {
      <div class="card mt-4">
        <div class="flex items-start justify-between gap-4">
          <div>
            <h3 class="text-lg font-semibold text-slate-900">Transaction {{ tx.id }}</h3>
            <p class="text-sm text-slate-500">{{ tx.merchant }} - {{ tx.userId }}</p>
          </div>
          <button type="button" class="btn-ghost" (click)="selectedTx.set(null)">Close</button>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
          <section>
            <h4 class="section-title">Transaction fields</h4>
            <dl class="grid grid-cols-2 gap-3 text-sm">
              <dt class="text-slate-500">Amount</dt><dd>KES {{ tx.amount | number: '1.0-0' }}</dd>
              <dt class="text-slate-500">Currency</dt><dd>{{ tx.currency }}</dd>
              <dt class="text-slate-500">Timestamp</dt><dd>{{ tx.ts | date: 'medium' }}</dd>
              <dt class="text-slate-500">IP</dt><dd>{{ tx.userIp || 'Unknown' }}</dd>
              <dt class="text-slate-500">Model</dt><dd>{{ tx.modelVersion }}</dd>
              <dt class="text-slate-500">Simulated</dt><dd>{{ tx.isSimulated ? 'Yes' : 'No' }}</dd>
              <dt class="text-slate-500">Manual</dt><dd>{{ tx.isManual ? 'Yes' : 'No' }}</dd>
              <dt class="text-slate-500">Score</dt><dd>{{ tx.score | number: '1.2-2' }}</dd>
            </dl>
          </section>

          <section>
            <h4 class="section-title">Risk explanation</h4>
            @if (tx.reasons.length > 0) {
              <div class="space-y-3">
                @for (reason of tx.reasons; track reason.feature) {
                  <div>
                    <div class="flex items-center justify-between text-sm">
                      <span class="font-medium text-slate-700">{{ reason.feature }}</span>
                      <app-badge [value]="reason.direction" />
                    </div>
                    <div class="score-bar-track mt-1">
                      <div
                        class="score-bar-fill"
                        [style.width.%]="reason.contribution * 100"
                        [style.background-color]="reason.direction === 'HIGH' ? 'var(--color-fp-block-ring)' : 'var(--color-fp-allow-ring)'"
                      ></div>
                    </div>
                  </div>
                }
              </div>
            } @else {
              <p class="text-sm text-slate-500">No material risk factors for this transaction.</p>
            }
          </section>
        </div>

        <div class="fp-divider"></div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <section>
            <h4 class="section-title">Lifecycle</h4>
            <div class="flex items-center gap-3">
              <app-badge [value]="tx.lifecycleStatus" />
              @if (tx.lifecycleStatus === 'AUTHORIZED') {
                <button type="button" class="btn-primary" (click)="settle(tx.id)">Mark as Settled</button>
              }
            </div>
          </section>

          <section>
            <h4 class="section-title">Linked case</h4>
            @if (tx.caseId) {
              <a class="btn-secondary" [routerLink]="['/cases', tx.caseId]">Open {{ tx.caseId }}</a>
            } @else {
              <p class="text-sm text-slate-500">No linked case</p>
            }
          </section>
        </div>
      </div>
    }
  `,
})
export class TransactionListComponent {
  protected txService = inject(TransactionService);

  decisionFilter = signal<DecisionFilter>('ALL');
  userIdFilter = signal('');
  scoreFilter = signal<ScoreFilter>('ANY');
  page = signal(1);
  selectedTx = signal<Transaction | null>(null);

  private userDebounce: ReturnType<typeof setTimeout> | null = null;

  filtered = computed(() => {
    const bounds = this.scoreBounds();
    return this.txService.filtered({
      decision: this.decisionFilter() === 'ALL' ? undefined : this.decisionFilter(),
      userId: this.userIdFilter() || undefined,
      minScore: bounds.minScore,
      maxScore: bounds.maxScore,
    });
  });

  totalPages = computed(() => Math.max(1, Math.ceil(this.filtered().length / 25)));
  paginated = computed(() => {
    const start = (this.page() - 1) * 25;
    return this.filtered().slice(start, start + 25);
  });
  rangeStart = computed(() => (this.filtered().length === 0 ? 0 : (this.page() - 1) * 25 + 1));
  rangeEnd = computed(() => Math.min(this.page() * 25, this.filtered().length));

  setDecision(value: string): void {
    this.decisionFilter.set(value as DecisionFilter);
    this.page.set(1);
  }

  setScore(value: string): void {
    this.scoreFilter.set(value as ScoreFilter);
    this.page.set(1);
  }

  setUserId(value: string): void {
    if (this.userDebounce) clearTimeout(this.userDebounce);
    this.userDebounce = setTimeout(() => {
      this.userIdFilter.set(value);
      this.page.set(1);
    }, 300);
  }

  resetFilters(): void {
    this.decisionFilter.set('ALL');
    this.userIdFilter.set('');
    this.scoreFilter.set('ANY');
    this.page.set(1);
  }

  settle(id: string): void {
    // TODO: confirm dialog before calling service
    this.txService.settleTransaction(id);
    const current = this.txService.getById(id);
    if (current) this.selectedTx.set(current);
  }

  rescore(id: string): void {
    this.txService.rescoreTransaction(id);
  }

  rescoreSelected(): void {
    const tx = this.selectedTx();
    if (tx) this.rescore(tx.id);
  }

  private scoreBounds(): { minScore?: number; maxScore?: number } {
    switch (this.scoreFilter()) {
      case 'LOW':
        return { maxScore: 0.39 };
      case 'MEDIUM':
        return { minScore: 0.4, maxScore: 0.79 };
      case 'HIGH':
        return { minScore: 0.8 };
      default:
        return {};
    }
  }
}
