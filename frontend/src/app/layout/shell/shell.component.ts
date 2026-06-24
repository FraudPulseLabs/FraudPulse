import { Component, computed, inject, signal } from '@angular/core';
import { Router, RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { ToastService } from '../../core/services/toast.service';
import { ConfirmDialogComponent } from '../../shared/components/confirm-dialog/confirm-dialog.component';
import { ThemeToggleComponent } from '../../shared/components/theme-toggle/theme-toggle.component';
import { FpIconsModule } from '../../shared/icons/fp-icons.module';

interface NavItem {
  path:  string;
  label: string;
  icon:  string;
}

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, ConfirmDialogComponent, ThemeToggleComponent, FpIconsModule],
  template: `
    <div class="min-h-screen md:flex md:h-screen md:overflow-hidden" style="background-color: var(--fp-bg)">
      @if (navOpen()) {
        <button
          type="button"
          class="fixed inset-0 z-30 md:hidden"
          style="background-color: var(--fp-overlay)"
          aria-label="Close navigation"
          (click)="closeNav()"
        ></button>
      }

      <aside
        class="fp-sidebar fixed inset-y-0 left-0 z-40 flex w-[min(15rem,72vw)] flex-col border-r transition-transform duration-200 md:static md:w-60 md:max-w-none md:translate-x-0"
        [class.-translate-x-full]="!navOpen()"
        style="background-color: var(--fp-sidebar-bg); border-color: var(--fp-sidebar-border)"
      >
        <div class="border-b px-4 py-4 md:px-5 md:py-5" style="border-color: var(--fp-sidebar-border)">
          <div class="flex items-center gap-2.5">
            <span
              class="flex h-7 w-7 items-center justify-center rounded-sm text-[10px] font-bold tracking-tighter"
              style="background-color: var(--fp-brand-mark-bg); color: var(--fp-brand-mark-text)"
            >FP</span>
            <div>
              <p class="text-sm font-semibold tracking-tight fp-sidebar-text">FraudPulse</p>
              <p class="text-xs fp-sidebar-text-muted">Detection System</p>
            </div>
          </div>
        </div>

        <nav class="flex-1 space-y-0.5 overflow-y-auto px-2.5 py-4 md:px-3">
          @for (item of navItems; track item.path) {
            <a
              [routerLink]="item.path"
              routerLinkActive="nav-link-active"
              [routerLinkActiveOptions]="{ exact: false }"
              class="nav-link"
              (click)="closeNav()"
            >
              <lucide-icon class="fp-icon" [name]="item.icon" [size]="18" [strokeWidth]="1.75" aria-hidden="true" />
              {{ item.label }}
            </a>
          }
        </nav>

        <div class="border-t px-2.5 py-4 md:px-3" style="border-color: var(--fp-sidebar-border)">
          <div class="flex items-center gap-2 px-2 py-2">
            <div
              class="flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold"
              style="background-color: #dc2626; color: #fff"
            >
              {{ userInitial() }}
            </div>
            <div class="min-w-0 flex-1">
              <p class="truncate text-xs font-semibold fp-sidebar-text">{{ userEmail() || 'Signed in' }}</p>
              <p class="truncate text-xs fp-sidebar-text-muted">FraudPulse analyst</p>
            </div>
          </div>
          <button
            type="button"
            class="fp-sidebar-logout mt-1 flex w-full items-center gap-2 rounded-sm px-2 py-2 text-left text-xs font-medium fp-sidebar-text-muted"
            (click)="confirmingLogout.set(true)"
          >
            <lucide-icon class="fp-icon" name="log-out" [size]="16" [strokeWidth]="1.75" aria-hidden="true" />
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
        <header
          class="sticky top-0 z-20 flex min-h-14 shrink-0 items-center justify-between border-b px-4 sm:px-6"
          style="background-color: var(--fp-header-bg); border-color: var(--fp-header-border)"
        >
          <div class="flex min-w-0 items-center gap-3">
            <button
              type="button"
              class="inline-flex h-10 w-10 items-center justify-center rounded-sm border md:hidden fp-text-secondary"
              style="border-color: var(--fp-border)"
              aria-label="Open navigation"
              (click)="toggleNav()"
            >
              <lucide-icon name="menu" [size]="20" [strokeWidth]="1.75" aria-hidden="true" />
            </button>
            <div class="min-w-0">
              <h1 class="truncate text-sm font-semibold tracking-tight fp-text-primary sm:text-base">FraudPulse Analytics</h1>
              <p class="text-xs fp-text-muted md:hidden">Fraud operations console</p>
            </div>
          </div>
          <div class="flex items-center gap-3">
            <app-theme-toggle />
            <span class="fp-status-badge hidden sm:inline-flex">
              <span class="fp-status-badge__dot" aria-hidden="true"></span>
              System Active
            </span>
          </div>
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
    { path: 'overview',     label: 'Overview',          icon: 'activity' },
    { path: 'transactions', label: 'Transactions',      icon: 'credit-card' },
    { path: 'alerts',       label: 'Alert Queue',         icon: 'bell' },
    { path: 'cases',        label: 'Cases',             icon: 'folder-open' },
    { path: 'watchlist',    label: 'Watchlist',         icon: 'eye' },
    { path: 'model-demo',   label: 'Model Validation',  icon: 'flask-conical' },
  ];

  toggleNav(): void {
    this.navOpen.update((value) => !value);
  }

  closeNav(): void {
    this.navOpen.set(false);
  }
}
