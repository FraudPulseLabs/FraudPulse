import { DatePipe, DecimalPipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { TransactionService } from '../../../core/services/transaction.service';
import type { Transaction, TransactionFeatures } from '../../../core/models';
import { BadgeComponent } from '../../../shared/components/badge/badge.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { ScoreBarComponent } from '../../../shared/components/score-bar/score-bar.component';

type DecisionFilter = 'ALL' | 'ALLOW' | 'REVIEW' | 'BLOCK';
type ScoreFilter = 'ANY' | 'LOW' | 'MEDIUM' | 'HIGH';

type FeatureFormat = 'boolean' | 'currency' | 'integer' | 'number' | 'ratio';

interface FeatureField {
  key: keyof TransactionFeatures;
  format: FeatureFormat;
}

interface FeatureSection {
  title: string;
  fields: FeatureField[];
}

const FEATURE_SECTIONS: FeatureSection[] = [
  {
    title: 'Behavioral signals',
    fields: [
      { key: 'enriched_amount_usd', format: 'currency' },
      { key: 'hour_sin', format: 'number' },
      { key: 'hour_cos', format: 'number' },
      { key: 'dow_sin', format: 'number' },
      { key: 'dow_cos', format: 'number' },
      { key: 'is_weekend', format: 'boolean' },
      { key: 'is_night', format: 'boolean' },
      { key: 'cross_border', format: 'boolean' },
      { key: 'seconds_since_last_txn', format: 'integer' },
      { key: 'txn_count_1h', format: 'integer' },
      { key: 'txn_count_24h', format: 'integer' },
    ],
  },
  {
    title: 'Card history and velocity',
    fields: [
      { key: 'card_txn_count_prior', format: 'integer' },
      { key: 'card_avg_amount_usd_prior', format: 'currency' },
      { key: 'card_std_amount_usd_prior', format: 'currency' },
      { key: 'amount_vs_card_avg', format: 'ratio' },
      { key: 'amount_zscore', format: 'number' },
      { key: 'high_amount_relative', format: 'boolean' },
      { key: 'cross_border_high_amount', format: 'boolean' },
      { key: 'velocity_spike_1h', format: 'boolean' },
      { key: 'weak_auth_high_value', format: 'boolean' },
    ],
  },
  {
    title: 'Encoded model inputs',
    fields: [
      { key: 'cvv2_result_enc', format: 'integer' },
      { key: 'avs_result_enc', format: 'integer' },
      { key: 'pan_entry_mode_enc', format: 'integer' },
      { key: 'authentication_enc', format: 'integer' },
      { key: 'card_type_Credit', format: 'integer' },
      { key: 'card_type_Debit', format: 'integer' },
      { key: 'card_type_Prepaid', format: 'integer' },
      { key: 'channel_ATM', format: 'integer' },
      { key: 'channel_ECOMMERCE', format: 'integer' },
      { key: 'channel_POS', format: 'integer' },
      { key: 'transaction_type_purchase', format: 'integer' },
      { key: 'transaction_type_withdrawal', format: 'integer' },
      { key: 'merchant_category_code_fraud_rate', format: 'ratio' },
      { key: 'transaction_country_fraud_rate', format: 'ratio' },
    ],
  },
];

@Component({
  selector: 'app-transaction-list',
  standalone: true,
  imports: [BadgeComponent, DatePipe, DecimalPipe, EmptyStateComponent, RouterLink, ScoreBarComponent],
  template: `
    <div class="page-header">
      <div class="min-w-0">
        <h2 class="page-title">Transaction Monitor</h2>
        <p class="text-sm fp-text-secondary">
          Live fraud scoring decisions from the API.
        </p>
      </div>
      <button type="button" class="btn-ghost" (click)="rescoreSelected()">Rescore selected</button>
    </div>

    @if (error()) {
      <div class="card mb-4 border border-red-200 bg-red-50 text-sm text-red-700">{{ error() }}</div>
    }

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
      @if (loading()) {
        <p class="p-6 text-sm fp-text-secondary">Loading transactions…</p>
      } @else if (filtered().length === 0) {
        <app-empty-state message="No transactions match these filters" />
      } @else {
        <div class="space-y-3 md:hidden">
          @for (tx of paginated(); track tx.id) {
            <article class="rounded-sm border border-[var(--fp-border)] bg-[var(--fp-surface)] p-4">
              <div class="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p class="fp-data-mono">{{ tx.id }}</p>
                  <p class="mt-1 fp-data-cell !text-sm">{{ tx.ts | date: 'dd MMM, HH:mm' }} · {{ tx.userId }}</p>
                </div>
                <app-badge [value]="tx.decision" />
              </div>
              <div class="mt-4 fp-table-divide">
                <div class="flex items-center justify-between gap-3 py-2">
                  <span class="fp-text-muted text-sm font-medium">Merchant</span>
                  <span class="max-w-[60%] text-right fp-data-cell">{{ tx.merchant }}</span>
                </div>
                <div class="flex items-center justify-between gap-3 py-2">
                  <span class="fp-text-muted text-sm font-medium">Amount</span>
                  <span class="fp-data-cell">KES {{ tx.amount | number: '1.0-0' }}</span>
                </div>
                <div class="flex items-center justify-between gap-3 py-2">
                  <span class="fp-text-muted text-sm font-medium">Status</span>
                  <app-badge [value]="tx.lifecycleStatus" />
                </div>
              </div>
              <div class="mt-4 flex items-center gap-3">
                <div class="min-w-0 flex-1">
                  <app-score-bar [score]="tx.score" />
                </div>
                <button type="button" class="btn-secondary" (click)="openTransaction(tx)">Open</button>
              </div>
            </article>
          }
        </div>

        <div class="hidden overflow-auto md:block">
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
                  <td><span class="fp-data-mono" [title]="tx.id">{{ tx.id }}</span></td>
                  <td>{{ tx.userId }}</td>
                  <td>{{ tx.merchant }}</td>
                  <td>KES {{ tx.amount | number: '1.0-0' }}</td>
                  <td><app-score-bar [score]="tx.score" /></td>
                  <td><app-badge [value]="tx.decision" /></td>
                  <td><app-badge [value]="tx.lifecycleStatus" /></td>
                  <td>
                    <button type="button" class="btn-ghost" (click)="openTransaction(tx)">Open</button>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>

        <div class="mt-4 flex flex-col gap-3 text-sm fp-text-secondary sm:flex-row sm:items-center sm:justify-between">
          <span>Showing {{ rangeStart() }}-{{ rangeEnd() }} of {{ filtered().length }} results</span>
          <div class="flex flex-wrap items-center gap-2">
            <button type="button" class="btn-secondary" [disabled]="page() === 1" (click)="page.set(page() - 1)">Previous</button>
            <span class="text-xs">Page {{ page() }} / {{ totalPages() }}</span>
            <button type="button" class="btn-secondary" [disabled]="page() === totalPages()" (click)="page.set(page() + 1)">Next</button>
          </div>
        </div>
      }
    </div>

    @if (selectedTx(); as tx) {
      <div class="fixed inset-0 z-40" style="background-color: var(--fp-overlay)" (click)="closeTransaction()"></div>
      <section class="fixed inset-x-0 bottom-0 z-50 h-[92vh] overflow-hidden rounded-t-sm border border-[var(--fp-border)] shadow-2xl md:inset-y-0 md:right-0 md:left-auto md:h-auto md:w-[min(720px,92vw)] md:max-h-none md:rounded-none md:rounded-l-sm" style="background-color: var(--fp-surface)">
        <div class="flex h-full flex-col">
          <div class="flex flex-col gap-4 border-b border-[var(--fp-border)] px-4 py-4 sm:px-6">
            <div class="flex items-start justify-between gap-4">
              <div class="min-w-0">
                <p class="text-xs font-semibold uppercase tracking-[0.24em] fp-text-muted">Transaction detail</p>
                <h3 class="mt-1 text-lg font-semibold fp-text-primary">Transaction {{ tx.id }}</h3>
                <p class="text-sm fp-text-secondary">{{ tx.merchant }} - {{ tx.userId }}</p>
              </div>
              <button type="button" class="btn-ghost" (click)="closeTransaction()">Close</button>
            </div>
            <div class="flex flex-wrap items-center gap-2">
              <app-badge [value]="tx.decision" />
              <app-badge [value]="tx.lifecycleStatus" />
              <span class="rounded-full bg-[var(--fp-hover)] px-3 py-1 text-xs font-medium fp-text-secondary">Score {{ tx.score | number: '1.2-2' }}</span>
            </div>
          </div>

          <div class="flex-1 overflow-y-auto overscroll-contain px-4 py-4 sm:px-6 sm:py-6">
            @if (detailLoading()) {
              <p class="text-sm fp-text-secondary">Loading transaction detail…</p>
            }
            <div class="grid grid-cols-1 gap-6 xl:grid-cols-2" [class.opacity-50]="detailLoading()">
              <section>
                <h4 class="section-title">Transaction fields</h4>
                <dl class="fp-detail-grid">
                  <dt>Amount</dt><dd>KES {{ tx.amount | number: '1.0-0' }}</dd>
                  <dt>Currency</dt><dd>{{ tx.currency }}</dd>
                  <dt>Timestamp</dt><dd>{{ tx.ts | date: 'medium' }}</dd>
                  <dt>IP</dt><dd>{{ tx.userIp || 'Unknown' }}</dd>
                  <dt>Model</dt><dd>{{ tx.modelVersion }}</dd>
                  <dt>Simulated</dt><dd>{{ tx.isSimulated ? 'Yes' : 'No' }}</dd>
                  <dt>Manual</dt><dd>{{ tx.isManual ? 'Yes' : 'No' }}</dd>
                  <dt>Score</dt><dd>{{ tx.score | number: '1.2-2' }}</dd>
                </dl>
              </section>

              <section>
                <h4 class="section-title">Risk explanation</h4>
                @if (tx.reasons.length > 0) {
                  <div class="space-y-3">
                    @for (reason of tx.reasons; track reason.feature) {
                      <div>
                        <div class="flex items-center justify-between text-sm">
                          <span class="font-medium fp-text-secondary">{{ reason.feature }}</span>
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
                  <p class="text-sm fp-text-secondary">No material risk factors for this transaction.</p>
                }
              </section>
            </div>

            <div class="fp-divider"></div>

            <div class="grid grid-cols-1 gap-6 xl:grid-cols-2">
              <section>
                <h4 class="section-title">Lifecycle</h4>
                <div class="flex flex-wrap items-center gap-3">
                  <app-badge [value]="tx.lifecycleStatus" />
                  @if (tx.lifecycleStatus === 'AUTHORIZED') {
                    <button type="button" class="btn-primary" (click)="settle(tx.id)">Mark as Settled</button>
                  }
                </div>
              </section>

              <section>
                <h4 class="section-title">Linked case</h4>
                @if (tx.caseId) {
                  <a class="btn-secondary" [routerLink]="['/cases', tx.caseId]" (click)="closeTransaction()">Open {{ tx.caseId }}</a>
                } @else {
                  <p class="text-sm fp-text-secondary">No linked case</p>
                }
              </section>
            </div>

            <div class="fp-divider"></div>

            <section>
              <h4 class="section-title">Model features</h4>
              <div class="grid grid-cols-1 gap-4 xl:grid-cols-3">
                @for (section of featureSections; track section.title) {
                  <div class="rounded-xl border border-[var(--fp-border)] bg-[var(--fp-surface-muted)] p-4">
                    <h5 class="mb-3 text-sm font-semibold fp-text-primary">{{ section.title }}</h5>
                    <dl class="fp-feature-list">
                      @for (field of section.fields; track field.key) {
                        <div class="fp-feature-row">
                          <dt class="fp-feature-key">{{ field.key }}</dt>
                          <dd class="fp-feature-value">{{ formatFeature(tx.features, field) }}</dd>
                        </div>
                      }
                    </dl>
                  </div>
                }
              </div>
            </section>
          </div>
        </div>
      </section>
    }
  `,
})
export class TransactionListComponent implements OnInit {
  protected txService = inject(TransactionService);
  protected featureSections = FEATURE_SECTIONS;

  decisionFilter = signal<DecisionFilter>('ALL');
  userIdFilter = signal('');
  scoreFilter = signal<ScoreFilter>('ANY');
  page = signal(1);
  selectedTx = signal<Transaction | null>(null);
  detailLoading = signal(false);

  readonly loading = this.txService.loading;
  readonly error = this.txService.error;

  private userDebounce: ReturnType<typeof setTimeout> | null = null;

  ngOnInit(): void {
    void this.txService.loadTransactions();
  }

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

  openTransaction(tx: Transaction): void {
    this.selectedTx.set(tx);

    this.detailLoading.set(true);
    void this.txService
      .fetchTransactionById(tx.id)
      .then((detail) => {
        if (detail) this.selectedTx.set(detail);
      })
      .finally(() => this.detailLoading.set(false));
  }

  closeTransaction(): void {
    this.selectedTx.set(null);
  }

  formatFeature(features: TransactionFeatures, field: FeatureField): string {
    const value = features[field.key];

    switch (field.format) {
      case 'boolean':
        return value ? 'Yes' : 'No';
      case 'currency':
        return `$${Number(value).toFixed(2)}`;
      case 'integer':
        return `${Math.round(Number(value))}`;
      case 'ratio':
        return Number(value).toFixed(3);
      default:
        return Number(value).toFixed(4);
    }
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
