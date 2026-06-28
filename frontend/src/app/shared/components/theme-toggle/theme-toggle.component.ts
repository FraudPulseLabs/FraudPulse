import { Component, inject } from '@angular/core';
import { ThemeService } from '../../../core/services/theme.service';
import { FpIconsModule } from '../../icons/fp-icons.module';

@Component({
  selector: 'app-theme-toggle',
  standalone: true,
  imports: [FpIconsModule],
  template: `
    <button
      type="button"
      class="theme-toggle"
      (click)="theme.toggle()"
      [attr.aria-label]="theme.isDark() ? 'Switch to light mode' : 'Switch to dark mode'"
      [attr.aria-pressed]="theme.isDark()"
    >
      @if (theme.isDark()) {
        <lucide-icon name="sun" [size]="16" [strokeWidth]="1.75" aria-hidden="true" />
      } @else {
        <lucide-icon name="moon" [size]="16" [strokeWidth]="1.75" aria-hidden="true" />
      }
    </button>
  `,
})
export class ThemeToggleComponent {
  readonly theme = inject(ThemeService);
}
