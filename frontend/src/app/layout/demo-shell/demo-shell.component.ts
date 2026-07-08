import { Component, computed, inject, signal } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { ThemeToggleComponent } from '../../shared/components/theme-toggle/theme-toggle.component';
import { FpIconsModule } from '../../shared/icons/fp-icons.module';

interface DemoNavItem {
  path: string;
  label: string;
  icon: string;
}

/**
 * Public, unauthenticated layout for the pre-access demo dashboard. Visitors
 * can explore Model Validation and the Live Pipeline Demo before requesting
 * access — no session required. The guest identity block replaces the analyst
 * profile/logout of the authenticated shell.
 */
@Component({
  selector: 'app-demo-shell',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, ThemeToggleComponent, FpIconsModule],
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
          <a routerLink="/" class="flex items-center gap-2.5 no-underline">
            <span
              class="flex h-7 w-7 items-center justify-center rounded-sm text-[10px] font-bold tracking-tighter"
              style="background-color: var(--fp-brand-mark-bg); color: var(--fp-brand-mark-text)"
            >FP</span>
            <div>
              <p class="text-sm font-semibold tracking-tight fp-sidebar-text">FraudPulse</p>
              <p class="text-xs fp-sidebar-text-muted">Demo Preview</p>
            </div>
          </a>
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
              style="background-color: var(--fp-hover); color: var(--fp-sidebar-text)"
            >G</div>
            <div class="min-w-0 flex-1">
              <p class="truncate text-xs font-semibold fp-sidebar-text">Guest account</p>
              <p class="truncate text-xs fp-sidebar-text-muted">Preview access</p>
            </div>
          </div>
          <a
            [routerLink]="['/']"
            fragment="access"
            class="mt-1 flex w-full items-center justify-center gap-2 rounded-sm px-2 py-2 text-xs font-semibold no-underline"
            style="background-color: var(--fp-brand-mark-bg); color: var(--fp-brand-mark-text)"
            (click)="closeNav()"
          >
            <lucide-icon class="fp-icon" name="sparkles" [size]="15" [strokeWidth]="1.75" aria-hidden="true" />
            Request access
          </a>
        </div>
      </aside>

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
              <h1 class="truncate text-sm font-semibold tracking-tight fp-text-primary sm:text-base">FraudPulse Demo</h1>
              <p class="text-xs fp-text-muted md:hidden">Public preview</p>
            </div>
          </div>
          <div class="flex items-center gap-3">
            <app-theme-toggle />
            <span class="fp-status-badge hidden sm:inline-flex">
              <span class="fp-status-badge__dot" aria-hidden="true"></span>
              System Active
            </span>
            @if (isAuthenticated()) {
              <a routerLink="/overview" class="text-xs font-semibold fp-text-secondary hover:fp-text-primary no-underline">
                Open dashboard →
              </a>
            } @else {
              <a routerLink="/login" class="inline-flex items-center gap-1.5 text-xs font-semibold fp-text-secondary hover:fp-text-primary no-underline">
                <lucide-icon class="fp-icon" name="log-in" [size]="15" [strokeWidth]="1.75" aria-hidden="true" />
                Sign in
              </a>
            }
          </div>
        </header>

        <main class="flex-1 overflow-auto p-4 sm:p-6">
          <router-outlet />
        </main>
      </div>
    </div>
  `,
})
export class DemoShellComponent {
  private readonly auth = inject(AuthService);

  navOpen = signal(false);

  readonly isAuthenticated = computed(() => this.auth.isAuthenticated());

  navItems: DemoNavItem[] = [
    { path: 'model-validation', label: 'Model Validation',  icon: 'flask-conical' },
    { path: 'live-pipeline',    label: 'Live Scoring Demo', icon: 'zap' },
  ];

  toggleNav(): void {
    this.navOpen.update((value) => !value);
  }

  closeNav(): void {
    this.navOpen.set(false);
  }
}
