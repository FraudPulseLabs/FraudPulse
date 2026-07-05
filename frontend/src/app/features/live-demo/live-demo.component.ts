import { CommonModule, DatePipe, DecimalPipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { environment } from '../../../environments/environment';
import { AuthService } from '../../core/services/auth.service';
import { FpIconsModule } from '../../shared/icons/fp-icons.module';
import type {
  FeatureContribution,
} from '../../core/models/transaction.model';

// ---------------------------------------------------------------------------
// Mirrors backend src/schemas/transaction_ingest.TransactionIngestRequest.
// This page posts to the real POST /api/v1/transactions endpoint (not the
// validation-only /demo/score endpoint), so every submission here persists a
// row, runs the live decision policy, and fires the same event_emitter
// signals that create review/decline alerts and cases. Use this page to
// demo the end-to-end flow; use Model Demo to validate model accuracy
// against the held-out set.
// ---------------------------------------------------------------------------

type CvvResult = 'MATCH' | 'NOT_PROVIDED' | 'NOT_APPLICABLE';
type AvsResult = 'FULL_MATCH' | 'PARTIAL_MATCH' | 'NOT_PERFORMED';
type PanEntryMode = 'CHIP' | 'CONTACTLESS' | 'ONLINE' | 'MAGSTRIPE';
type AuthenticationMethod = 'BIOMETRICS' | 'OTP' | 'PIN' | 'CVV2' | 'NONE';
type CardType = 'Debit' | 'Credit' | 'Prepaid';
type Channel = 'ATM' | 'ECOMMERCE' | 'POS';
type TransactionType = 'purchase' | 'withdrawal';

interface IngestPayload {
  card_id: string;
  merchant_id: string;
  timestamp: string;
  enriched_amount_usd: number;
  issuing_bank_country: string;
  transaction_country: string;
  cvv2_result: CvvResult;
  avs_result: AvsResult;
  pan_entry_mode: PanEntryMode;
  authentication: AuthenticationMethod;
  card_type: CardType;
  channel: Channel;
  transaction_type: TransactionType;
  merchant_category_code: string;
  transaction_city?: string | null;
  terminal_id?: string | null;
}

interface IngestResult {
  transaction_id: string;
  decision: 'APPROVE' | 'APPROVE_WITH_REVIEW' | 'DECLINE';
  score: number | null;
  model_name?: string | null;
  reason?: string | null;
  contributions?: FeatureContribution[] | null;
}

interface SubmittedEntry {
  id: string;
  payload: IngestPayload;
  bucket: PresetBucket;
  status: 'sending' | 'done' | 'error';
  result?: IngestResult;
  caseId?: string;
  error?: string;
}

type PresetBucket = 'APPROVE' | 'REVIEW' | 'DECLINE';

interface Preset {
  bucket: PresetBucket;
  label: string;
  helpText: string;
  cardId: string;
  generate: () => Omit<IngestPayload, 'card_id'>;
}


const MERCHANTS_LOW_RISK = ['MCH-GROCERY-014', 'MCH-PHARMACY-002', 'MCH-UTILITY-009'];
const MERCHANTS_HIGH_RISK = ['MCH-ELECTRONICS-118', 'MCH-GIFTCARD-077', 'MCH-CRYPTO-203'];
const COUNTRIES_DOMESTIC = 'KE';
const COUNTRIES_FOREIGN = ['NG', 'RU', 'VN', 'BR', 'PH'];
const MCC_LOW_RISK = ['5411', '5499', '4900'];
const MCC_HIGH_RISK = ['5816', '6051', '5967'];

function rand(min: number, max: number): number {
  return Math.random() * (max - min) + min;
}

function pick<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

function isoNow(hourOverride?: number): string {
  const d = new Date();
  if (hourOverride !== undefined) d.setHours(hourOverride, Math.floor(rand(0, 59)), 0, 0);
  return d.toISOString();
}

// ---------------------------------------------------------------------------
// Synthetic timestamp stepping for REVIEW and DECLINE presets.
//
// The model's seconds_since_last_txn feature has a ±2.5 SHAP swing and
// dominates outcomes when inter-click time is arbitrary (wall-clock gaps of
// minutes or hours push it strongly negative → APPROVE regardless of other
// risk signals). To control this we maintain a per-bucket synthetic clock that
// advances in small increments on each click, seeded 2 hours in the past so
// the very first submission already has a short predecessor on the next click.
//
// APPROVE is left on real wall-clock time — it should stay clean and the
// recency feature naturally helps legitimate domestic transactions.
// ---------------------------------------------------------------------------

const syntheticClock: Partial<Record<PresetBucket, number>> = {};

function nextSyntheticTs(bucket: PresetBucket, stepMinSec: number, stepMaxSec: number): string {
  const seed = syntheticClock[bucket] ?? (Date.now() / 1000 - 2 * 3600);
  const next = seed + rand(stepMinSec, stepMaxSec);
  syntheticClock[bucket] = next;
  return new Date(next * 1000).toISOString();
}

// REVIEW: 30-120 s between clicks — realistic e-commerce session velocity.
function reviewTs(): string { return nextSyntheticTs('REVIEW', 30, 120); }

// DECLINE: 15-45 s between clicks — rapid burst, helps is_velocity_burst_last_1h
// fire and keeps seconds_since_last_txn short (positive SHAP contribution).
function declineTs(): string { return nextSyntheticTs('DECLINE', 15, 45); }

const PRESETS: Preset[] = [
  {
    bucket: 'APPROVE',
    label: 'Likely Approve',
    helpText: 'Domestic, card-present, modest amount, strong auth — clean transaction profile.',
    cardId: 'DEMO-APPROVE-CARD-01',
    generate: () => ({
      merchant_id: pick(MERCHANTS_LOW_RISK),
      timestamp: isoNow(rand(9, 18)),
      enriched_amount_usd: Number(rand(8, 60).toFixed(2)),
      issuing_bank_country: COUNTRIES_DOMESTIC,
      transaction_country: COUNTRIES_DOMESTIC,
      cvv2_result: 'MATCH',
      avs_result: 'FULL_MATCH',
      pan_entry_mode: 'CHIP', // card-present, pairs with PIN
      authentication: 'PIN',
      card_type: 'Credit',
      channel: 'POS',
      transaction_type: 'purchase',
      merchant_category_code: pick(MCC_LOW_RISK),
    }),
  },
  {
    bucket: 'REVIEW',
    label: 'Likely Review',
    helpText: 'One moderate flag — cross-border or weak auth. Timestamp steps forward in short increments to keep seconds_since_last_txn positive across clicks.',
    cardId: 'DEMO-REVIEW-CARD-01',
    generate: () => {
      const crossBorderVariant = Math.random() < 0.5;
      return {
        merchant_id: pick(MERCHANTS_LOW_RISK.concat(MERCHANTS_HIGH_RISK)),
        timestamp: reviewTs(),
        enriched_amount_usd: Number(rand(150, 500).toFixed(2)),
        issuing_bank_country: COUNTRIES_DOMESTIC,
        transaction_country: crossBorderVariant ? pick(COUNTRIES_FOREIGN) : COUNTRIES_DOMESTIC,
        // ONLINE entry is always card-not-present; CVV2/OTP are valid CNP auth methods.
        cvv2_result: crossBorderVariant ? 'MATCH' : 'NOT_PROVIDED',
        avs_result: 'PARTIAL_MATCH',
        pan_entry_mode: 'ONLINE',
        authentication: crossBorderVariant ? 'OTP' : 'CVV2',
        card_type: 'Debit',
        channel: 'ECOMMERCE',
        transaction_type: 'purchase',
        merchant_category_code: pick(MCC_LOW_RISK.concat(MCC_HIGH_RISK)),
      };
    },
  },
  {
    bucket: 'DECLINE',
    label: 'Likely Decline',
    helpText: 'Stacked risk: cross-border, very large amount, no auth, high-risk MCC. Timestamp steps in rapid 15-45 s bursts to trigger velocity features and keep seconds_since_last_txn positive. First click may still APPROVE — second and beyond should decline reliably.',
    cardId: 'DEMO-DECLINE-CARD-01',
    generate: () => ({
      merchant_id: pick(MERCHANTS_HIGH_RISK),
      timestamp: declineTs(),
      enriched_amount_usd: Number(rand(3000, 9000).toFixed(2)),
      issuing_bank_country: COUNTRIES_DOMESTIC,
      transaction_country: pick(COUNTRIES_FOREIGN),
      // ONLINE/NONE/NOT_PROVIDED/NOT_PERFORMED: no verification at all — realistic high-risk CNP.
      cvv2_result: 'NOT_PROVIDED',
      avs_result: 'NOT_PERFORMED',
      pan_entry_mode: 'ONLINE',
      authentication: 'NONE',
      card_type: 'Prepaid',
      channel: 'ECOMMERCE',
      transaction_type: 'purchase',
      merchant_category_code: pick(MCC_HIGH_RISK),
    }),
  },
];

@Component({
  selector: 'app-live-demo',
  standalone: true,
  imports: [CommonModule, DatePipe, DecimalPipe, RouterLink, FpIconsModule],
  template: `
    <div class="space-y-4">
      <header class="card">
        <h1 class="text-lg font-semibold fp-text-primary">Live Scoring Demo</h1>
        <p class="mt-1 text-sm fp-text-secondary">
          Sends real transactions through <code>POST /api/v1/transactions</code> — the same
          path production traffic uses. Each submission is persisted, scored, decisioned, and
          (for review or decline outcomes) triggers the same alert and case creation as a real
          transaction. Use this page to demo the full flow end to end.
        </p>
        <p class="mt-2 rounded border-l-4 border-sky-400 bg-sky-50 px-3 py-2 text-xs text-sky-900">
          <strong>Note:</strong> REVIEW and DECLINE presets use a synthetic timestamp that steps
          forward in short increments per click, keeping <code>seconds_since_last_txn</code>
          small and positive so the actual risk signals drive the outcome. APPROVE uses real
          wall-clock time and should remain clean. The first DECLINE click on a fresh page load
          may still APPROVE — the second click onward should decline reliably.
        </p>
      </header>

      @if (!isAuthenticated()) {
        <div class="card flex flex-col items-center gap-3 py-10 text-center">
          <span
            class="flex h-11 w-11 items-center justify-center rounded-full"
            style="background-color: var(--fp-hover); color: var(--fp-text-secondary)"
          >
            <lucide-icon name="lock" [size]="20" [strokeWidth]="1.75" aria-hidden="true" />
          </span>
          <h2 class="text-base font-semibold fp-text-primary">Sign in to run the live pipeline</h2>
          <p class="max-w-md text-sm fp-text-secondary">
            This demo posts real transactions through the production pipeline — each one is
            persisted, scored and can open alerts and cases. It's available to signed-in analysts.
            <span class="fp-text-muted">The Model Validation page is fully usable without signing in.</span>
          </p>
          <a routerLink="/login" class="btn-primary mt-1 inline-flex items-center gap-2 px-4 py-2 no-underline">
            <lucide-icon name="log-in" [size]="16" [strokeWidth]="1.75" aria-hidden="true" />
            Sign in to continue
          </a>
        </div>
      } @else {
      <div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
        @for (preset of presets; track preset.bucket) {
          <div class="card flex flex-col gap-2">
            <div class="flex items-center justify-between">
              <span
                class="inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium"
                [class]="bucketBadgeClass(preset.bucket)"
              >{{ preset.label }}</span>
              <span class="fp-data-mono text-[11px] fp-text-muted">{{ preset.cardId }}</span>
            </div>
            <p class="text-xs fp-text-secondary">{{ preset.helpText }}</p>
            <button
              type="button"
              class="btn-primary !min-h-0 px-3 py-1.5 mt-auto"
              [disabled]="sendingPreset() !== null"
              (click)="submit(preset)"
            >
              {{ sendingPreset() === preset.bucket ? 'Sending…' : 'Generate & Send' }}
            </button>
          </div>
        }
      </div>

      <div class="card overflow-x-auto !p-0">
        <table class="fp-table fp-table--compact min-w-full">
          <thead>
            <tr>
              <th>Time</th>
              <th>Preset</th>
              <th>Card</th>
              <th>Country</th>
              <th class="text-right">Amount (USD)</th>
              <th>Auth</th>
              <th>Outcome</th>
              <th class="text-right">Score</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            @for (entry of entries(); track entry.id) {
              <tr class="align-top">
                <td class="fp-data-mono">{{ entry.payload.timestamp | date:'short' }}</td>
                <td>
                  <span
                    class="inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium"
                    [class]="bucketBadgeClass(entry.bucket)"
                  >{{ entry.bucket }}</span>
                </td>
                <td class="fp-data-mono">{{ entry.payload.card_id }}</td>
                <td>{{ entry.payload.issuing_bank_country }} → {{ entry.payload.transaction_country }}</td>
                <td class="text-right fp-data-mono">{{ entry.payload.enriched_amount_usd | number:'1.2-2' }}</td>
                <td>{{ entry.payload.authentication }}</td>
                <td>
                  @if (entry.status === 'sending') {
                    <span class="fp-text-muted">…</span>
                  } @else if (entry.status === 'error') {
                    <span class="text-rose-600 font-medium" [title]="entry.error">error</span>
                  } @else if (entry.result; as r) {
                    <span
                      class="inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium"
                      [class]="decisionBadgeClass(r.decision)"
                    >{{ r.decision }}</span>
                    @if (r.reason) {
                      <span class="ml-2 italic fp-text-secondary text-[11px]">{{ r.reason }}</span>
                    }
                  }
                </td>
                <td class="text-right fp-data-mono">
                  @if (entry.result?.score != null) {
                    {{ entry.result!.score | number:'1.4-4' }}
                  } @else { — }
                </td>
                <td class="text-right">
                  @if (entry.result?.decision === 'APPROVE_WITH_REVIEW' && entry.caseId) {
                    <a
                      [routerLink]="['/cases', entry.caseId]"
                      class="text-xs text-sky-700 underline"
                      (click)="$event.stopPropagation()"
                    >View case →</a>
                  }
                </td>
              </tr>
              @if (entry.result?.contributions?.length) {
                <tr>
                  <td colspan="9" class="bg-[var(--fp-surface-muted)] px-3 py-2 text-[11px] fp-text-secondary border-b fp-row-divider">
                    <span class="fp-data-cell !text-[11px]">Top contributions:</span>
                    @for (c of topContribs(entry.result!.contributions!); track c.feature) {
                      <span class="ml-3 inline-flex items-center gap-1 fp-data-mono !text-[11px]">
                        {{ c.feature }}
                        <span [class.text-rose-700]="c.shap_value > 0" [class.text-emerald-700]="c.shap_value < 0">
                          ({{ c.shap_value > 0 ? '+' : '' }}{{ c.shap_value | number:'1.3-3' }})
                        </span>
                      </span>
                    }
                  </td>
                </tr>
              }
            } @empty {
              <tr>
                <td colspan="9" class="px-3 py-6 text-center fp-data-cell">
                  No transactions sent yet. Pick a preset above to start.
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
export class LiveDemoComponent {
  private http = inject(HttpClient);
  private auth = inject(AuthService);

  readonly isAuthenticated = computed(() => this.auth.isAuthenticated());

  presets = PRESETS;
  entries = signal<SubmittedEntry[]>([]);
  sendingPreset = signal<PresetBucket | null>(null);

  submit(preset: Preset): void {
    this.sendingPreset.set(preset.bucket);
    const payload: IngestPayload = {
      card_id: preset.cardId,
      ...preset.generate(),
    };

    const entryId = crypto.randomUUID();

    const entry: SubmittedEntry = {
      id: entryId,
      payload,
      bucket: preset.bucket,
      status: 'sending'
    };
    this.entries.update((rows) => [entry, ...rows]);

    this.http
      .post<IngestResult>(`${environment.apiUrl}/api/v1/transactions?explain=true`, payload)
      .subscribe({
        next: (result) => {
          this.updateEntry(entryId, {
            status: 'done',
            result,
          });

          this.sendingPreset.set(null);

          if (result.decision === 'APPROVE_WITH_REVIEW') {
            this.lookupCase(entryId, result.transaction_id);
          }
        },
        error: (err) => {
          // No transaction_id on error — fall back to timestamp+card key isn't possible here,
          // so we mark the pending entry (still status:'sending') by finding it.
          this.entries.update((rows) => {
            const idx = rows.findIndex((r) => r.status === 'sending');
            if (idx === -1) return rows;
            const updated = [...rows];
            updated[idx] = { ...updated[idx], status: 'error', error: this.formatError(err) };
            return updated;
          });
          this.sendingPreset.set(null);
        },
      });
  }

  private lookupCase(entryId: string, transactionId: string): void {
    this.http
      .get<Array<{ id: string; transaction_id: string }>>(`${environment.apiUrl}/api/v1/cases`)
      .subscribe({
        next: (cases) => {
          const match = cases.find((c) => c.transaction_id === transactionId);
          if (match) this.updateEntry(entryId, { caseId: match.id });
        },
        error: () => { /* silently ignore — link just won't appear */ },
      });
  }

  private updateEntry(id: string, patch: Partial<SubmittedEntry>): void {
    this.entries.update(rows =>
      rows.map(row =>
        row.id === id
          ? { ...row, ...patch }
          : row
      )
    );
  }

  private formatError(err: { error?: { detail?: unknown }; message?: string }): string {
    const detail = err?.error?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item) => (typeof item === 'object' && item && 'msg' in item ? String(item.msg) : String(item)))
        .join('; ');
    }
    return err?.message ?? 'Request failed';
  }

  topContribs(contribs: FeatureContribution[]): FeatureContribution[] {
    return [...contribs]
      .sort((a, b) => Math.abs(b.shap_value) - Math.abs(a.shap_value))
      .slice(0, 5);
  }

  bucketBadgeClass(bucket: PresetBucket): string {
    if (bucket === 'DECLINE') return 'bg-rose-100 text-rose-800';
    if (bucket === 'REVIEW') return 'bg-amber-100 text-amber-800';
    return 'bg-emerald-100 text-emerald-800';
  }

  decisionBadgeClass(decision: IngestResult['decision']): string {
    if (decision === 'DECLINE') return 'bg-rose-100 text-rose-800';
    if (decision === 'APPROVE_WITH_REVIEW') return 'bg-amber-100 text-amber-800';
    return 'bg-emerald-100 text-emerald-800';
  }
}