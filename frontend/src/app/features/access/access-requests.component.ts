import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import {
  AccessRequestRecord,
  AccessRequestService,
} from '../../core/services/access-request.service';
import { ToastService } from '../../core/services/toast.service';
import { ConfirmDialogComponent } from '../../shared/components/confirm-dialog/confirm-dialog.component';
import { EmptyStateComponent } from '../../shared/components/empty-state/empty-state.component';
import { TimeAgoPipe } from '../../shared/pipes/time-ago.pipe';

type StatusFilter = 'ALL' | 'pending' | 'approved' | 'rejected';

interface ApprovedInfo {
  email: string;
  tempPassword: string | null;
}

/** Progress messages shown while the (slow) Supabase provisioning runs. */
const APPROVE_STEPS = [
  'Creating the Supabase account…',
  'Issuing a temporary password…',
  'Finalising the approval…',
];

@Component({
  selector: 'app-access-requests',
  standalone: true,
  imports: [ConfirmDialogComponent, EmptyStateComponent, TimeAgoPipe],
  template: `
    <div class="page-header">
      <div>
        <h2 class="page-title">Access requests</h2>
        <p class="text-sm fp-text-secondary">
          Early-access submissions from the public landing page.
        </p>
      </div>
      <button
        type="button"
        class="cta-solid"
        [disabled]="loading()"
        (click)="load()"
      >
        {{ loading() ? 'Refreshing…' : 'Refresh' }}
      </button>
    </div>

    @if (error()) {
      <div class="card mb-4 border border-red-200 bg-red-50 text-sm text-red-700">
        {{ error() }}
      </div>
    }

    <div class="card mb-4">
      <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div
          class="inline-flex rounded-sm border border-[var(--fp-border)] p-1"
          style="background-color: var(--fp-surface)"
        >
          @for (status of statuses; track status) {
            <button
              type="button"
              class="px-3 py-1.5 rounded-sm text-sm font-medium capitalize"
              [class.fp-tab-active]="statusFilter() === status"
              [class.fp-text-secondary]="statusFilter() !== status"
              (click)="statusFilter.set(status)"
            >
              {{ status }}
            </button>
          }
        </div>

        <div class="flex flex-wrap items-center gap-3 text-sm fp-text-secondary">
          <span>Total: <strong class="fp-text-primary">{{ requests().length }}</strong></span>
          <span>Pending: <strong class="fp-text-primary">{{ counts().pending }}</strong></span>
          <span>Approved: <strong class="fp-text-primary">{{ counts().approved }}</strong></span>
          <span>Rejected: <strong class="fp-text-primary">{{ counts().rejected }}</strong></span>
        </div>
      </div>
    </div>

    <div class="card overflow-hidden">
      @if (loading() && requests().length === 0) {
        <p class="p-6 text-sm fp-text-secondary">Loading access requests…</p>
      } @else if (filtered().length === 0) {
        <app-empty-state
          icon="Inbox"
          message="No access requests"
          subtext="Submissions from the landing page will appear here."
        />
      } @else {
        <div class="overflow-auto">
          <table class="fp-table">
            <thead>
              <tr>
                <th>Submitted</th>
                <th>Email</th>
                <th>Company</th>
                <th>Status</th>
                <th class="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              @for (req of filtered(); track req.id) {
                <tr>
                  <td>{{ req.created_at | timeAgo }}</td>
                  <td><span class="fp-data-mono">{{ req.email }}</span></td>
                  <td>{{ req.company || '—' }}</td>
                  <td>
                    <span
                      [class.badge-low]="req.status === 'approved'"
                      [class.badge-medium]="req.status === 'pending'"
                      [class.badge-high]="req.status === 'rejected'"
                    >
                      {{ req.status }}
                    </span>
                  </td>
                  <td class="text-right">
                    @if (req.status === 'pending') {
                      <button
                        type="button"
                        class="btn-primary"
                        (click)="confirmApprove(req)"
                        [disabled]="approving()"
                      >
                        Approve
                      </button>
                    } @else if (req.status === 'approved') {
                      <span class="text-sm fp-text-secondary">Approved</span>
                    } @else {
                      <span class="text-sm fp-text-secondary">—</span>
                    }
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      }
    </div>

    <app-confirm-dialog
      [open]="!!pendingApprove()"
      title="Approve access request"
      [message]="
        'Approve ' +
        (pendingApprove()?.email ?? '') +
        '? This creates their Supabase login and issues a password so they can sign in.'
      "
      confirmLabel="Approve"
      confirmVariant="primary"
      (confirmed)="onApproveConfirmed($event)"
    />

    @if (approving()) {
      <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
        <div class="card w-96 text-center">
          <div
            class="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-2 border-[var(--fp-border)]"
            style="border-top-color: #6366f1"
            aria-hidden="true"
          ></div>
          <p class="page-title mb-1">Approving access…</p>
          <p class="text-sm fp-text-primary mb-3" aria-live="polite">{{ approveStep() }}</p>
          <p class="text-xs fp-text-secondary">
            Setting up their account can take several seconds. Please keep this window open —
            we'll show the login details as soon as it's done.
          </p>
        </div>
      </div>
    }

    @if (approvedInfo(); as info) {
      <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
        <div class="card w-96">
          <p class="page-title mb-1">Access approved</p>
          <p class="text-sm fp-text-secondary mb-4">
            <span class="fp-data-mono">{{ info.email }}</span> can now sign in to FraudPulse.
          </p>

          @if (info.tempPassword) {
            <div class="mb-4">
              <span class="fp-label">Temporary password</span>
              <div class="flex items-center gap-2">
                <code
                  class="fp-data-mono flex-1 rounded-sm border border-[var(--fp-border)] px-3 py-2 text-sm"
                  style="background-color: var(--fp-surface)"
                  >{{ info.tempPassword }}</code
                >
                <button
                  type="button"
                  class="btn-secondary"
                  (click)="copyPassword(info.tempPassword)"
                >
                  Copy
                </button>
              </div>
              <p class="mt-2 text-xs fp-text-secondary">
                Share this with {{ info.email }} — it won't be shown again.
              </p>
            </div>
          } @else {
            <p class="mb-4 text-sm fp-text-secondary">
              This email already had a Supabase account, so no new password was issued.
            </p>
          }

          <div class="flex justify-end">
            <button type="button" class="btn-primary" (click)="approvedInfo.set(null)">
              Done
            </button>
          </div>
        </div>
      </div>
    }
  `,
})
export class AccessRequestsComponent implements OnInit, OnDestroy {
  private readonly service = inject(AccessRequestService);
  private readonly toast = inject(ToastService);

  readonly statuses: StatusFilter[] = ['ALL', 'pending', 'approved', 'rejected'];
  readonly statusFilter = signal<StatusFilter>('ALL');

  readonly requests = signal<AccessRequestRecord[]>([]);
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);

  readonly pendingApprove = signal<AccessRequestRecord | null>(null);
  readonly approving = signal(false);
  readonly approvedInfo = signal<ApprovedInfo | null>(null);

  private readonly approveStepIndex = signal(0);
  readonly approveStep = computed(() => APPROVE_STEPS[this.approveStepIndex()]);
  private approveTimer: ReturnType<typeof setInterval> | null = null;

  readonly counts = computed(() => {
    const all = this.requests();
    return {
      pending: all.filter(r => r.status === 'pending').length,
      approved: all.filter(r => r.status === 'approved').length,
      rejected: all.filter(r => r.status === 'rejected').length,
    };
  });

  readonly filtered = computed(() => {
    const f = this.statusFilter();
    const all = this.requests();
    return f === 'ALL' ? all : all.filter(r => r.status === f);
  });

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.error.set(null);
    this.loading.set(true);
    this.service.list().subscribe({
      next: (res) => {
        this.requests.set(res.data ?? []);
        this.loading.set(false);
      },
      error: (err: HttpErrorResponse) => {
        this.loading.set(false);
        if (err.status === 0) {
          this.error.set('Cannot reach the API. Is the backend running?');
        } else if (err.status === 401) {
          this.error.set('Your session has expired. Please sign in again.');
        } else {
          const detail = (err.error as { detail?: string } | null)?.detail;
          this.error.set(detail || 'Failed to load access requests.');
        }
      },
    });
  }

  confirmApprove(req: AccessRequestRecord): void {
    this.pendingApprove.set(req);
  }

  onApproveConfirmed(confirmed: boolean): void {
    const pending = this.pendingApprove();
    this.pendingApprove.set(null);
    if (!confirmed || !pending) return;

    this.approving.set(true);
    this.startApproveProgress();
    this.service.approve(pending.id).subscribe({
      next: (res) => {
        this.stopApproveProgress();
        this.approving.set(false);
        const newStatus = res.data?.status ?? 'approved';
        this.requests.update((list) =>
          list.map((r) => (r.id === pending.id ? { ...r, status: newStatus } : r)),
        );
        this.toast.success('Access request approved.');
        this.approvedInfo.set({
          email: pending.email,
          tempPassword: res.temp_password ?? null,
        });
      },
      error: (err: HttpErrorResponse) => {
        this.stopApproveProgress();
        this.approving.set(false);
        const detail = (err.error as { detail?: string } | null)?.detail;
        this.toast.error(detail || 'Failed to approve the request.');
      },
    });
  }

  /** Advance the loading message through the steps while provisioning runs. */
  private startApproveProgress(): void {
    this.approveStepIndex.set(0);
    this.stopApproveProgress();
    this.approveTimer = setInterval(() => {
      this.approveStepIndex.update((i) => Math.min(i + 1, APPROVE_STEPS.length - 1));
    }, 1600);
  }

  private stopApproveProgress(): void {
    if (this.approveTimer) {
      clearInterval(this.approveTimer);
      this.approveTimer = null;
    }
  }

  ngOnDestroy(): void {
    this.stopApproveProgress();
  }

  copyPassword(password: string): void {
    navigator.clipboard?.writeText(password).then(
      () => this.toast.success('Password copied to clipboard.'),
      () => this.toast.error('Could not copy to clipboard.'),
    );
  }
}
