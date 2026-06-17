import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';
import { ToastService } from '../../../core/services/toast.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [FormsModule],
  template: `
    <div class="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div class="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <div class="mb-6 flex items-center gap-2">
          <div class="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-500">
            <span class="text-sm font-bold text-white">FP</span>
          </div>
          <div>
            <p class="text-base font-semibold text-slate-800">FraudPulse</p>
            <p class="text-xs text-slate-400">Sign in to continue</p>
          </div>
        </div>

        <form (ngSubmit)="submit()" class="space-y-4">
          <div>
            <label for="email" class="mb-1 block text-xs font-medium text-slate-600">Email</label>
            <input
              id="email"
              type="email"
              name="email"
              autocomplete="email"
              required
              [ngModel]="email()"
              (ngModelChange)="email.set($event)"
              class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-800 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label for="password" class="mb-1 block text-xs font-medium text-slate-600">Password</label>
            <input
              id="password"
              type="password"
              name="password"
              autocomplete="current-password"
              required
              [ngModel]="password()"
              (ngModelChange)="password.set($event)"
              class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-800 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          @if (error()) {
            <p class="rounded-lg bg-red-50 px-3 py-2 text-xs font-medium text-red-700">{{ error() }}</p>
          }

          <button
            type="submit"
            [disabled]="loading()"
            class="w-full rounded-lg bg-indigo-500 px-3 py-2 text-sm font-semibold text-white transition hover:bg-indigo-600 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {{ loading() ? 'Signing in…' : 'Sign in' }}
          </button>
        </form>
      </div>
    </div>
  `,
})
export class LoginComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly toast = inject(ToastService);

  readonly email = signal('');
  readonly password = signal('');
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);

  async submit(): Promise<void> {
    if (this.loading()) return;
    this.error.set(null);
    this.loading.set(true);
    try {
      const email = this.email().trim();
      await this.auth.signIn(email, this.password());
      await this.router.navigateByUrl('/transactions');
      this.toast.success(`Welcome back, ${email}`);
    } catch (err: unknown) {
      // Login failures stay inline (next to the form), not in a toast.
      this.error.set(err instanceof Error ? err.message : 'Sign in failed. Check your credentials.');
    } finally {
      this.loading.set(false);
    }
  }
}
