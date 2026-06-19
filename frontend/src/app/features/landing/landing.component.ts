import { DecimalPipe } from '@angular/common';
import { Component, OnDestroy, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AccessRequestService } from '../../core/services/access-request.service';
import { ThemeToggleComponent } from '../../shared/components/theme-toggle/theme-toggle.component';

type ScanStatus = 'unverified' | 'secured' | 'flagged';

interface ScanEvent {
  id: string;
  ref: string;
  amount: string;
  corridor: string;
  status: ScanStatus;
  latencyMs: number | null;
}

const MERCHANTS = [
  'ledger://wire-eu',
  'ach://settlement',
  'card://auth-capture',
  'swift://mt103',
  'rtp://fednow',
  'sepa://instant',
];

@Component({
  selector: 'app-landing',
  standalone: true,
  imports: [DecimalPipe, RouterLink, FormsModule, ThemeToggleComponent],
  templateUrl: './landing.component.html',
  styleUrl: './landing.component.css',
})
export class LandingComponent implements OnInit, OnDestroy {
  private readonly accessRequests = inject(AccessRequestService);

  readonly accessEmail = signal('');
  readonly accessCompany = signal('');
  readonly accessSubmitting = signal(false);
  readonly accessError = signal('');
  readonly accessSuccess = signal('');
  readonly events = signal<ScanEvent[]>([]);
  readonly throughput = signal(0);
  readonly avgLatency = signal(0.42);

  private intervalId: ReturnType<typeof setInterval> | null = null;
  private seq = 0;
  private secured = 0;
  private totalLatency = 0;
  private resolved = 0;

  ngOnInit(): void {
    for (let i = 0; i < 6; i++) {
      this.pushEvent('unverified');
    }
    this.intervalId = setInterval(() => this.tick(), 1400);
  }

  ngOnDestroy(): void {
    if (this.intervalId) clearInterval(this.intervalId);
  }

  scrollTo(id: string): void {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  submitAccess(): void {
    const email = this.accessEmail().trim();
    if (!email || this.accessSubmitting()) return;

    this.accessError.set('');
    this.accessSuccess.set('');
    this.accessSubmitting.set(true);

    this.accessRequests
      .submit({
        email,
        company: this.accessCompany().trim() || undefined,
      })
      .subscribe({
        next: (res) => {
          this.accessSubmitting.set(false);
          this.accessSuccess.set(res.message);
          this.accessEmail.set('');
          this.accessCompany.set('');
        },
        error: (err) => {
          this.accessSubmitting.set(false);
          const detail = err.error?.detail;
          if (typeof detail === 'string') {
            this.accessError.set(detail);
          } else if (Array.isArray(detail) && detail[0]?.msg) {
            this.accessError.set(detail[0].msg);
          } else if (err.status === 0) {
            this.accessError.set('Cannot reach the server. Please try again shortly.');
          } else {
            this.accessError.set('Unable to submit your request. Please try again.');
          }
        },
      });
  }

  statusLabel(status: ScanStatus): string {
    switch (status) {
      case 'unverified':
        return 'Unverified';
      case 'secured':
        return 'Secured';
      case 'flagged':
        return 'Flagged';
    }
  }

  private tick(): void {
    const current = this.events();
    const pending = current.filter(e => e.status === 'unverified');
    if (pending.length > 0 && Math.random() > 0.25) {
      const target = pending[pending.length - 1];
      const latency = +(0.18 + Math.random() * 0.62).toFixed(2);
      const flagged = Math.random() < 0.12;
      this.events.update(list =>
        list.map(e =>
          e.id === target.id
            ? {
                ...e,
                status: flagged ? 'flagged' : 'secured',
                latencyMs: latency,
              }
            : e,
        ),
      );
      this.resolved += 1;
      this.totalLatency += latency;
      if (!flagged) this.secured += 1;
      this.avgLatency.set(+(this.totalLatency / this.resolved).toFixed(2));
      this.throughput.set(this.secured);
    }
    this.pushEvent('unverified');
  }

  private pushEvent(status: ScanStatus): void {
    this.seq += 1;
    const event: ScanEvent = {
      id: `evt-${this.seq}`,
      ref: `TX-${String(100000 + this.seq).slice(-6)}`,
      amount: `$${(120 + Math.random() * 48000).toFixed(2)}`,
      corridor: MERCHANTS[Math.floor(Math.random() * MERCHANTS.length)],
      status,
      latencyMs: null,
    };
    this.events.update(list => [event, ...list].slice(0, 8));
  }
}
