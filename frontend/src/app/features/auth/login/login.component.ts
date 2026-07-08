import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';
import { ToastService } from '../../../core/services/toast.service';
import { ThemeToggleComponent } from '../../../shared/components/theme-toggle/theme-toggle.component';
import { FpIconsModule } from '../../../shared/icons/fp-icons.module';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [FormsModule, RouterLink, ThemeToggleComponent, FpIconsModule],
  templateUrl: './login.component.html',
  styleUrl: './login.component.css',
})
export class LoginComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly toast = inject(ToastService);

  readonly email = signal('');
  readonly password = signal('');
  // Honeypot: bots that autofill every input will populate it. Any non-empty
  // value short-circuits sign-in so the credentials never leave the browser.
  readonly website = signal('');
  readonly showPassword = signal(false);
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);

  togglePasswordVisibility(): void {
    this.showPassword.update(v => !v);
  }

  async submit(): Promise<void> {
    if (this.loading()) return;
    if (this.website().trim()) {
      // Silently fail closed — same UX as an invalid password so bots can't
      // fingerprint the honeypot.
      this.error.set('Sign in failed. Check your credentials.');
      return;
    }
    this.error.set(null);
    this.loading.set(true);
    try {
      const email = this.email().trim();
      await this.auth.signIn(email, this.password());
      await this.router.navigateByUrl('/overview');
      this.toast.success(`Welcome back, ${email}`);
    } catch (err: unknown) {
      this.error.set(err instanceof Error ? err.message : 'Sign in failed. Check your credentials.');
    } finally {
      this.loading.set(false);
    }
  }
}
