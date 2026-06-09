import { Component, computed, inject, signal } from '@angular/core';
import { Router, RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { ToastService } from '../../core/services/toast.service';
import { ConfirmDialogComponent } from '../../shared/components/confirm-dialog/confirm-dialog.component';

interface NavItem {
  path:  string;
  label: string;
  icon:  string;
}

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, ConfirmDialogComponent],
  template: `
    <div class="min-h-screen bg-slate-50 md:flex md:h-screen md:overflow-hidden">
      @if (navOpen()) {
        <button
          type="button"
          class="fixed inset-0 z-30 bg-slate-950/40 md:hidden"
          aria-label="Close navigation"
          (click)="closeNav()"
        ></button>
      }

      <aside
        class="fixed inset-y-0 left-0 z-40 flex w-72 max-w-[85vw] flex-col transition-transform duration-200 md:static md:w-60 md:max-w-none md:translate-x-0"
        [class.-translate-x-full]="!navOpen()"
        style="background-color: var(--color-fp-navy-900)"
      >
        <div class="border-b border-white/10 px-5 py-5">
          <div class="flex items-center gap-2">
            <div class="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-500">
              <span class="text-xs font-bold text-white">FP</span>
            </div>
            <div>
              <p class="text-sm font-semibold text-white">FraudPulse</p>
              <p class="text-xs text-slate-400">Detection System</p>
            </div>
          </div>
        </div>

        <nav class="flex-1 space-y-0.5 overflow-y-auto px-3 py-4">
          @for (item of navItems; track item.path) {
            <a
              [routerLink]="item.path"
              routerLinkActive="nav-link-active"
              [routerLinkActiveOptions]="{ exact: false }"
              class="nav-link"
              (click)="closeNav()"
            >
              <span class="text-base">{{ item.icon }}</span>
              {{ item.label }}
            </a>
          }
        </nav>

        <div class="border-t border-white/10 px-3 py-4">
          <div class="flex items-center gap-2 px-2 py-2">
            <div class="flex h-7 w-7 items-center justify-center rounded-full bg-indigo-500">
              <span class="text-xs font-medium text-white">{{ userInitial() }}</span>
            </div>
            <div class="min-w-0 flex-1">
              <p class="truncate text-xs font-medium text-white">{{ userEmail() || 'Signed in' }}</p>
              <p class="truncate text-xs text-slate-400">FraudPulse analyst</p>
            </div>
          </div>
          <button
            type="button"
            class="mt-1 flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-xs font-medium text-slate-300 transition hover:bg-white/5 hover:text-white"
            (click)="confirmingLogout.set(true)"
          >
            <span class="text-base">⎋</span>
            Log out
          </button>
        </div>
      </aside>

      <app-confirm-dialog
        [open]="confirmingLogout()"
        title="Log out"
        message="You'll need to sign in again to continue. Log out now?"
        (confirmed)="onLogoutConfirmed($event)"
      />

      <div class="flex min-h-screen min-w-0 flex-1 flex-col md:min-h-0 md:overflow-hidden">
        <header class="sticky top-0 z-20 flex min-h-14 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-4 sm:px-6">
          <div class="flex min-w-0 items-center gap-3">
            <button
              type="button"
              class="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 text-slate-600 md:hidden"
              aria-label="Open navigation"
              (click)="toggleNav()"
            >
              ☰
            </button>
            <div class="min-w-0">
              <h1 class="truncate text-sm font-medium text-slate-700 sm:text-base">FraudPulse Analytics</h1>
              <p class="text-xs text-slate-400 md:hidden">Fraud operations console</p>
            </div>
          </div>
          <span class="hidden items-center gap-1.5 rounded-full bg-green-50 px-2.5 py-1 text-xs font-medium text-green-700 sm:inline-flex">
            <span class="h-1.5 w-1.5 rounded-full bg-green-500"></span>
            System Active
          </span>
        </header>

        <main class="flex-1 overflow-auto p-4 sm:p-6">
          <router-outlet />
        </main>
      </div>
    </div>
  `,
})
export class ShellComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly toast = inject(ToastService);

  navOpen = signal(false);
  confirmingLogout = signal(false);

  readonly userEmail = computed(() => this.auth.user()?.email ?? '');
  readonly userInitial = computed(() => (this.userEmail()[0] ?? 'U').toUpperCase());

  async onLogoutConfirmed(confirmed: boolean): Promise<void> {
    this.confirmingLogout.set(false);
    if (!confirmed) return;
    await this.auth.signOut();
    await this.router.navigateByUrl('/login');
    this.toast.success('You have been logged out');
  }

  navItems: NavItem[] = [
    { path: 'transactions', label: 'Transactions', icon: '💳' },
    { path: 'alerts',       label: 'Alert Queue',  icon: '🔔' },
    { path: 'cases',        label: 'Cases',        icon: '📁' },
    { path: 'watchlist',    label: 'Watchlist',    icon: '👁' },
    { path: 'metrics',      label: 'Metrics',      icon: '📊' },
    { path: 'model-demo',   label: 'Model Demo',   icon: '🧪' },
  ];

  toggleNav(): void {
    this.navOpen.update((value) => !value);
  }

  closeNav(): void {
    this.navOpen.set(false);
  }
}
