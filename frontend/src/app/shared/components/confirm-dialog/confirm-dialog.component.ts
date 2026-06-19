import { Component, input, output } from '@angular/core';

@Component({
  selector: 'app-confirm-dialog',
  standalone: true,
  template: `
    @if (open()) {
      <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
        <div class="card w-80">
          <p class="page-title mb-2">{{ title() }}</p>
          <p class="text-sm fp-text-secondary mb-4">{{ message() }}</p>
          <div class="flex justify-end gap-2">
            <button class="btn-secondary" (click)="confirmed.emit(false)">Cancel</button>
            <button class="btn-danger"    (click)="confirmed.emit(true)">Confirm</button>
          </div>
        </div>
      </div>
    }
  `,
})
export class ConfirmDialogComponent {
  open    = input(false);
  title   = input('Confirm');
  message = input('Are you sure?');
  confirmed = output<boolean>();
}
