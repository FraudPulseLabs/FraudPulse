import { Injectable, signal } from '@angular/core';

export type ToastType = 'success' | 'error' | 'info';

export interface Toast {
  id: number;
  type: ToastType;
  message: string;
}

/**
 * Shared, app-wide snackbar/toast queue. Inject anywhere and call
 * `success` / `error` / `info`. Toasts auto-dismiss; identical visible toasts
 * are de-duped (their timer restarts) so a failed batch collapses to one.
 */
@Injectable({ providedIn: 'root' })
export class ToastService {
  private static readonly DURATION_MS = 4000;

  private seq = 0;
  private readonly timers = new Map<number, ReturnType<typeof setTimeout>>();
  private readonly _toasts = signal<Toast[]>([]);

  readonly toasts = this._toasts.asReadonly();

  success(message: string): void {
    this.show('success', message);
  }

  error(message: string): void {
    this.show('error', message);
  }

  info(message: string): void {
    this.show('info', message);
  }

  show(type: ToastType, message: string): void {
    const existing = this._toasts().find(t => t.type === type && t.message === message);
    if (existing) {
      this.arm(existing.id); // already on screen — just refresh its lifetime
      return;
    }
    const id = ++this.seq;
    this._toasts.update(list => [...list, { id, type, message }]);
    this.arm(id);
  }

  dismiss(id: number): void {
    const timer = this.timers.get(id);
    if (timer) {
      clearTimeout(timer);
      this.timers.delete(id);
    }
    this._toasts.update(list => list.filter(t => t.id !== id));
  }

  private arm(id: number): void {
    const prev = this.timers.get(id);
    if (prev) clearTimeout(prev);
    this.timers.set(id, setTimeout(() => this.dismiss(id), ToastService.DURATION_MS));
  }
}
