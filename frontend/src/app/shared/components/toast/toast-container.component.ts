import { Component, inject } from '@angular/core';
import { ToastService, ToastType } from '../../../core/services/toast.service';

/**
 * Renders the ToastService queue as a stack of snackbars (top-right).
 * Mount once near the app root so it overlays every route.
 */
@Component({
  selector: 'app-toast-container',
  standalone: true,
  template: `
    @if (toast.toasts().length) {
      <div
        class="pointer-events-none fixed right-4 top-4 z-[100] flex w-80 max-w-[calc(100vw-2rem)] flex-col gap-2"
      >
        @for (t of toast.toasts(); track t.id) {
          <div
            class="pointer-events-auto flex items-start gap-2 rounded-lg border px-3 py-2.5 shadow-md"
            [class]="styles(t.type)"
            role="status"
          >
            <span class="text-sm leading-5">{{ icon(t.type) }}</span>
            <p class="flex-1 text-xs font-medium leading-5">{{ t.message }}</p>
            <button
              type="button"
              class="text-xs leading-5 opacity-60 transition hover:opacity-100"
              aria-label="Dismiss"
              (click)="toast.dismiss(t.id)"
            >
              ✕
            </button>
          </div>
        }
      </div>
    }
  `,
})
export class ToastContainerComponent {
  readonly toast = inject(ToastService);

  styles(type: ToastType): string {
    switch (type) {
      case 'success':
        return 'border-emerald-200 bg-emerald-50 text-emerald-800';
      case 'error':
        return 'border-rose-200 bg-rose-50 text-rose-800';
      default:
        return 'border-slate-200 bg-white text-slate-700';
    }
  }

  icon(type: ToastType): string {
    switch (type) {
      case 'success':
        return '✓';
      case 'error':
        return '⚠';
      default:
        return 'ℹ';
    }
  }
}
