import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';
import { ToastService } from '../../../core/services/toast.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [FormsModule, RouterLink],
  templateUrl: './login.component.html',
  styleUrl: './login.component.css',
})
export class LoginComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly toast = inject(ToastService);

  readonly email = signal('');
  readonly password = signal('');
  readonly showPassword = signal(false);
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);

  togglePasswordVisibility(): void {
    this.showPassword.update(v => !v);
  }

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
      this.error.set(err instanceof Error ? err.message : 'Sign in failed. Check your credentials.');
    } finally {
      this.loading.set(false);
    }
  }
}
