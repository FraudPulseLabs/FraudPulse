import { Component, computed, input } from '@angular/core';

@Component({
  selector: 'app-badge',
  standalone: true,
  template: `<span [class]="badgeClass()">{{ displayLabel() }}</span>`,
})
export class BadgeComponent {
  value = input('');
  label = input<string | null>(null);
  cssClass = input<string | null>(null);

  displayLabel = computed(() => this.label() ?? this.value());
  badgeClass = computed(() => {
    const explicitClass = this.cssClass();
    if (explicitClass) return explicitClass;

    const map: Record<string, string> = {
      ALLOW: 'badge-allow',
      REVIEW: 'badge-review',
      BLOCK: 'badge-block',
      HIGH: 'badge-high',
      MEDIUM: 'badge-medium',
      LOW: 'badge-low',
      NEW: 'badge-new',
      ACKNOWLEDGED: 'badge-acknowledged',
      RESOLVED: 'badge-resolved',
      OPEN: 'badge-new',
      INVESTIGATING: 'badge-acknowledged',
      CLOSED: 'badge-resolved',
      AUTHORIZED: 'badge-acknowledged',
      SETTLED: 'badge-resolved',
    };
    return map[this.value()] ?? 'badge-low';
  });
}
