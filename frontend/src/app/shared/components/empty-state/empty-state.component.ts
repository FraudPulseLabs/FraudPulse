import { Component, input } from '@angular/core';

@Component({
  selector: 'app-empty-state',
  standalone: true,
  template: `
    <div class="empty-state">
      <div class="text-4xl mb-3">{{ icon() }}</div>
      <p class="text-sm font-medium text-slate-500">{{ message() }}</p>
      @if (subtext()) {
        <p class="text-xs text-slate-400 mt-1">{{ subtext() }}</p>
      }
    </div>
  `,
})
export class EmptyStateComponent {
  icon = input('No data');
  message = input('No items found');
  subtext = input('');
}
