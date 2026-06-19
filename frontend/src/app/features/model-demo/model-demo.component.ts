import { CommonModule, DatePipe, DecimalPipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { environment } from '../../../environments/environment';
import type {
  BackendDecision,
  DemoTransaction,
  FeatureContribution,
  ScoreResult,
} from '../../core/models/transaction.model';

interface DemoRow {
  data: DemoTransaction;
  status: 'idle' | 'scoring' | 'done' | 'error';
  result?: ScoreResult;
  error?: string;
}

@Component({
  selector: 'app-model-demo',
  standalone: true,
  imports: [CommonModule, DatePipe, DecimalPipe],
  template: `
    <div class="space-y-4">
      <header class="card">
        <h1 class="text-lg font-semibold fp-text-primary">Model Demo — held-out test split</h1>
        <p class="mt-1 text-sm fp-text-secondary">
          These {{ rows().length }} transactions come from the chronological 20% test
          split of the raw training dataset. The active model (version2 calibrated
          LightGBM) has <strong>never seen them</strong>. Each row is POSTed through
          the real pipeline at
          <code class="rounded bg-[var(--fp-hover)] px-1 py-0.5 text-xs">POST /api/v1/transactions?explain=true</code>;
          the ground-truth <code class="rounded bg-[var(--fp-hover)] px-1 py-0.5 text-xs">is_fraud</code>
          label is stripped before sending and is only used here for display.
        </p>
        <p class="mt-2 rounded border-l-4 border-amber-400 bg-amber-50 px-3 py-2 text-xs text-amber-800">
          <strong>Caveat:</strong> live ingest builds card-history features from prior
          rows in the live DB only — seeding just these 20 demo rows means each card
          starts with cold-start velocity/spend defaults. Offline test-set scores were
          computed with full pre-split history, so live scores will differ. This is
          still a genuine unseen-data evaluation of the calibrated model.
        </p>
      </header>

      <div class="card flex flex-wrap items-center gap-3 !p-3">
        <button
          type="button"
          class="btn-primary !min-h-0 px-3 py-1.5"
          [disabled]="batchScoring()"
          (click)="scoreAll()"
        >
          {{ batchScoring() ? 'Scoring…' : 'Score all' }}
        </button>
        <button
          type="button"
          class="btn-secondary !min-h-0 px-3 py-1.5"
          (click)="reset()"
        >
          Reset
        </button>
        <label class="ml-2 inline-flex items-center gap-2 text-xs fp-text-secondary">
          <input
            type="checkbox"
            class="h-4 w-4"
            [checked]="reviewCountsAsFlagged()"
            (change)="toggleReviewFlagged($event)"
          />
          Count APPROVE_WITH_REVIEW as “flagged”
        </label>

        @if (summary(); as s) {
          <div class="ml-auto flex flex-wrap items-center gap-4 text-xs fp-text-secondary">
            <span>Scored: <strong>{{ s.scored }}/{{ s.total }}</strong></span>
            <span class="text-emerald-700">TP: <strong>{{ s.tp }}</strong></span>
            <span class="text-rose-700">FN: <strong>{{ s.fn }}</strong></span>
            <span class="text-amber-700">FP: <strong>{{ s.fp }}</strong></span>
            <span class="fp-text-secondary">TN: <strong>{{ s.tn }}</strong></span>
            <span>
              Accuracy:
              <strong>{{ s.scored ? ((s.tp + s.tn) / s.scored | number:'1.0-2') : '—' }}</strong>
            </span>
          </div>
        }
      </div>

      <div class="card overflow-x-auto !p-0">
        <table class="fp-table fp-table--compact min-w-full">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Card</th>
              <th>Merchant</th>
              <th class="text-right">Amount (USD)</th>
              <th>Channel</th>
              <th>Auth</th>
              <th>Country</th>
              <th>Actual</th>
              <th>Predicted</th>
              <th class="text-right">Score</th>
              <th>Match</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            @for (row of rows(); track row.data.transaction_id) {
              <tr class="align-top">
                <td class="fp-data-mono">
                  {{ row.data.timestamp | date:'short' }}
                </td>
                <td class="fp-data-mono">
                  {{ row.data.card_id }}
                </td>
                <td class="fp-data-mono">
                  {{ row.data.merchant_id }}
                </td>
                <td class="text-right fp-data-mono">
                  {{ row.data.enriched_amount_usd | number:'1.2-2' }}
                </td>
                <td>{{ row.data.channel }}</td>
                <td>{{ row.data.authentication }}</td>
                <td>
                  {{ row.data.issuing_bank_country }} → {{ row.data.transaction_country }}
                </td>
                <td>
                  <span
                    class="inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium"
                    [class.bg-rose-100]="row.data.is_fraud === 1"
                    [class.text-rose-800]="row.data.is_fraud === 1"
                    [class.bg-emerald-100]="row.data.is_fraud === 0"
                    [class.text-emerald-800]="row.data.is_fraud === 0"
                  >
                    {{ row.data.is_fraud === 1 ? 'Fraud' : 'Legit' }}
                  </span>
                </td>
                <td>
                  @if (row.result?.decision; as d) {
                    <span
                      class="inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium"
                      [class]="decisionClass(d)"
                    >{{ d }}</span>
                  } @else if (row.status === 'scoring') {
                    <span class="fp-text-muted">…</span>
                  } @else if (row.status === 'error') {
                    <span class="text-rose-600 font-medium" [title]="row.error">error</span>
                  } @else {
                    <span class="fp-text-muted">unscored</span>
                  }
                </td>
                <td class="text-right fp-data-mono">
                  @if (row.result?.score != null) {
                    {{ row.result!.score | number:'1.4-4' }}
                  } @else { — }
                </td>
                <td>
                  @if (row.result) {
                    @if (matches(row)) {
                      <span class="inline-flex rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-medium text-emerald-800">✓ correct</span>
                    } @else {
                      <span class="inline-flex rounded-full bg-rose-100 px-2 py-0.5 text-[11px] font-medium text-rose-800">✗ incorrect</span>
                    }
                  }
                </td>
                <td class="text-right">
                  <button
                    type="button"
                    class="btn-secondary !min-h-0 px-2 py-1 text-[11px]"
                    [disabled]="row.status === 'scoring'"
                    (click)="scoreOne(row)"
                  >
                    {{ row.status === 'scoring' ? '…' : 'Score' }}
                  </button>
                </td>
              </tr>
              @if (row.result?.contributions?.length) {
                <tr>
                  <td colspan="12" class="bg-[var(--fp-surface-muted)] px-3 py-2 text-[11px] fp-text-secondary border-b fp-row-divider">
                    <span class="fp-data-cell !text-[11px]">Top contributions:</span>
                    @for (c of topContribs(row.result!.contributions!); track c.feature) {
                      <span class="ml-3 inline-flex items-center gap-1 fp-data-mono !text-[11px]">
                        {{ c.feature }}
                        <span [class.text-rose-700]="c.shap_value > 0" [class.text-emerald-700]="c.shap_value < 0">
                          ({{ c.shap_value > 0 ? '+' : '' }}{{ c.shap_value | number:'1.3-3' }})
                        </span>
                      </span>
                    }
                    @if (row.result?.reason) {
                      <span class="ml-3 italic fp-text-secondary">reason: {{ row.result?.reason }}</span>
                    }
                  </td>
                </tr>
              }
            } @empty {
              <tr>
                <td colspan="12" class="px-3 py-6 text-center fp-data-cell">
                  @if (loading()) { Loading demo transactions… }
                  @else if (loadError()) { <span class="text-rose-600">{{ loadError() }}</span> }
                  @else { No demo transactions available. }
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    </div>
  `,
})
export class ModelDemoComponent implements OnInit {
  private http = inject(HttpClient);

  rows = signal<DemoRow[]>([]);
  loading = signal(false);
  loadError = signal<string | null>(null);
  batchScoring = signal(false);
  reviewCountsAsFlagged = signal(false);

  summary = computed(() => {
    const rs = this.rows();
    const reviewFlag = this.reviewCountsAsFlagged();
    let tp = 0, fn = 0, fp = 0, tn = 0, scored = 0;
    for (const r of rs) {
      if (!r.result) continue;
      scored++;
      const predFraud =
        r.result.decision === 'DECLINE' ||
        (reviewFlag && r.result.decision === 'APPROVE_WITH_REVIEW');
      const actualFraud = r.data.is_fraud === 1;
      if (predFraud && actualFraud) tp++;
      else if (!predFraud && actualFraud) fn++;
      else if (predFraud && !actualFraud) fp++;
      else tn++;
    }
    return { total: rs.length, scored, tp, fn, fp, tn };
  });

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.loadError.set(null);
    this.http
      .get<DemoTransaction[]>(`${environment.apiUrl}/api/v1/demo/transactions`)
      .subscribe({
        next: (data) => {
          this.rows.set(data.map((d) => ({ data: d, status: 'idle' })));
          this.loading.set(false);
        },
        error: (err) => {
          this.loadError.set(err?.error?.detail ?? err?.message ?? 'Failed to load demo transactions.');
          this.loading.set(false);
        },
      });
  }

  reset(): void {
    this.rows.update((rs) => rs.map((r) => ({ data: r.data, status: 'idle' })));
  }

  toggleReviewFlagged(evt: Event): void {
    this.reviewCountsAsFlagged.set((evt.target as HTMLInputElement).checked);
  }

  scoreAll(): void {
    this.batchScoring.set(true);
    const todo = this.rows().filter((r) => r.status !== 'done' && r.status !== 'scoring');
    let remaining = todo.length;
    if (remaining === 0) {
      this.batchScoring.set(false);
      return;
    }
    for (const row of todo) {
      this.scoreOne(row, () => {
        remaining--;
        if (remaining === 0) this.batchScoring.set(false);
      });
    }
  }

  scoreOne(row: DemoRow, done?: () => void): void {
    this.updateRow(row.data.transaction_id, (r) => ({ ...r, status: 'scoring', error: undefined }));

    // CRITICAL: strip is_fraud and the raw-CSV transaction_id from the body.
    // Backend mints a new DB id and is_fraud is ground-truth only.
    const { is_fraud: _is_fraud, transaction_id: _tx_id, ...payload } = row.data;

    this.http
      .post<ScoreResult>(
        `${environment.apiUrl}/api/v1/transactions?explain=true`,
        payload,
      )
      .subscribe({
        next: (result) => {
          this.updateRow(row.data.transaction_id, (r) => ({ ...r, status: 'done', result }));
          done?.();
        },
        error: (err) => {
          this.updateRow(row.data.transaction_id, (r) => ({
            ...r,
            status: 'error',
            error: err?.error?.detail ?? err?.message ?? 'Score request failed',
          }));
          done?.();
        },
      });
  }

  matches(row: DemoRow): boolean {
    if (!row.result) return false;
    const predFraud =
      row.result.decision === 'DECLINE' ||
      (this.reviewCountsAsFlagged() && row.result.decision === 'APPROVE_WITH_REVIEW');
    return predFraud === (row.data.is_fraud === 1);
  }

  topContribs(contribs: FeatureContribution[]): FeatureContribution[] {
    return [...contribs]
      .sort((a, b) => Math.abs(b.shap_value) - Math.abs(a.shap_value))
      .slice(0, 5);
  }

  decisionClass(d: BackendDecision): string {
    if (d === 'DECLINE') return 'bg-rose-100 text-rose-800';
    if (d === 'APPROVE_WITH_REVIEW') return 'bg-amber-100 text-amber-800';
    return 'bg-emerald-100 text-emerald-800';
  }

  private updateRow(id: string, fn: (r: DemoRow) => DemoRow): void {
    this.rows.update((rs) => rs.map((r) => (r.data.transaction_id === id ? fn(r) : r)));
  }
}
