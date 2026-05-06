import { Component } from '@angular/core';
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
    <div class="flex h-screen overflow-hidden">

      <!-- Sidebar -->
      <aside class="w-60 shrink-0 flex flex-col"
             style="background-color: var(--color-fp-navy-900)">
        <!-- Logo -->
        <div class="px-5 py-5 border-b border-white/10">
          <div class="flex items-center gap-2">
            <div class="w-7 h-7 rounded-lg bg-indigo-500 flex items-center justify-center">
              <span class="text-white text-xs font-bold">FP</span>
            </div>
            <div>
              <p class="text-white text-sm font-semibold">FraudPulse</p>
              <p class="text-slate-400 text-xs">Detection System</p>
            </div>
          </div>
        </div>

        <!-- Nav -->
        <nav class="flex-1 px-3 py-4 space-y-0.5">
          @for (item of navItems; track item.path) {
            <a [routerLink]="item.path"
               routerLinkActive="nav-link-active"
               [routerLinkActiveOptions]="{ exact: false }"
               class="nav-link">
              <span class="text-base">{{ item.icon }}</span>
              {{ item.label }}
            </a>
          }
        </nav>

        <!-- User pill -->
        <div class="px-3 py-4 border-t border-white/10">
          <div class="flex items-center gap-2 px-2 py-2">
            <div class="w-7 h-7 rounded-full bg-indigo-500 flex items-center justify-center">
              <span class="text-white text-xs font-medium">A</span>
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-white text-xs font-medium truncate">Analyst</p>
              <p class="text-slate-400 text-xs truncate">analyst&#64;fraudpulse.demo</p>
            </div>
          </div>
        </div>
      </aside>

      <!-- Main content -->
      <div class="flex-1 flex flex-col min-w-0 overflow-hidden">

        <!-- Topbar -->
        <header class="h-14 shrink-0 bg-white border-b border-slate-200
                        flex items-center justify-between px-6">
          <h1 class="text-sm font-medium text-slate-700">FraudPulse Analytics</h1>
          <div class="flex items-center gap-2">
            <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full
                          bg-green-50 text-green-700 text-xs font-medium">
              <span class="w-1.5 h-1.5 rounded-full bg-green-500"></span>
              System Active
            </span>
          </div>
        </header>

        <!-- Page content -->
        <main class="flex-1 overflow-auto p-6">
          <router-outlet />
        </main>

      </div>
    </div>
  `,
})
export class ShellComponent {
  navItems: NavItem[] = [
    { path: 'transactions', label: 'Transactions', icon: '💳' },
    { path: 'alerts',       label: 'Alert Queue',  icon: '🔔' },
    { path: 'cases',        label: 'Cases',        icon: '📁' },
    { path: 'watchlist',    label: 'Watchlist',    icon: '👁' },
    { path: 'metrics',      label: 'Metrics',      icon: '📊' },
  ];
}
