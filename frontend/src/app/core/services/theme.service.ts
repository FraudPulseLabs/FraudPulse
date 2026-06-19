import { Injectable, effect, signal } from '@angular/core';

export type ThemeMode = 'light' | 'dark';

const STORAGE_KEY = 'fp-theme';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  readonly mode = signal<ThemeMode>(this.readStored());

  constructor() {
    effect(() => this.apply(this.mode()));
  }

  toggle(): void {
    this.mode.update((current) => (current === 'dark' ? 'light' : 'dark'));
    this.persist();
  }

  isDark(): boolean {
    return this.mode() === 'dark';
  }

  private readStored(): ThemeMode {
    if (typeof localStorage === 'undefined') return 'light';
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'light' || stored === 'dark') return stored;
    return 'light';
  }

  private persist(): void {
    localStorage.setItem(STORAGE_KEY, this.mode());
  }

  private apply(mode: ThemeMode): void {
    document.documentElement.setAttribute('data-fp-theme', mode);
    document.documentElement.style.colorScheme = mode;
  }
}
