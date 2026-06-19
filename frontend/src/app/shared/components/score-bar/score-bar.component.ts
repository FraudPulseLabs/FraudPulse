import { DecimalPipe } from '@angular/common';
import { Component, computed, input } from '@angular/core';

@Component({
  selector: 'app-score-bar',
  standalone: true,
  imports: [DecimalPipe],
  template: `
    <div class="flex items-center gap-2">
      <div class="score-bar-track w-16">
        <div class="score-bar-fill" [style.width.%]="pct()" [style.background-color]="colour()"></div>
      </div>
      <span class="text-xs font-mono fp-text-secondary">{{ score() | number: '1.2-2' }}</span>
    </div>
  `,
})
export class ScoreBarComponent {
  score = input.required<number>();
  pct = computed(() => this.score() * 100);
  colour = computed(() => {
    const s = this.score();
    if (s >= 0.8) return 'var(--color-fp-block-ring)';
    if (s >= 0.4) return 'var(--color-fp-review-ring)';
    return 'var(--color-fp-allow-ring)';
  });
}
