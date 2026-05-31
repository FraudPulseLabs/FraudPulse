import { Component, signal } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';

interface NavItem {
  path:  string;
  label: string;
  icon:  string;
}

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
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
              <span class="text-xs font-medium text-white">A</span>
            </div>
            <div class="min-w-0 flex-1">
              <p class="truncate text-xs font-medium text-white">Analyst</p>
              <p class="truncate text-xs text-slate-400">analyst&#64;fraudpulse.demo</p>
            </div>
          </div>
        </div>
      </aside>

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
  navOpen = signal(false);

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
