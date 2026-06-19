//frontend\src\app\features\cases\case-list\case-list.component.ts
import { Component, computed, inject, signal, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { CaseService } from '../../../core/services/case.service';
import type { CaseStatus } from '../../../core/models';
import { BadgeComponent } from '../../../shared/components/badge/badge.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { TimeAgoPipe } from '../../../shared/pipes/time-ago.pipe';

type CaseFilter = 'ACTIVE' | 'ALL' | CaseStatus;

@Component({
  selector: 'app-case-list',
  standalone: true,
  imports: [BadgeComponent, EmptyStateComponent, TimeAgoPipe],
  template: `
    <div class="page-header">
      <div>
        <h2 class="page-title">Cases</h2>
        <p class="text-sm fp-text-secondary">Investigation workspace — cases are created automatically when fraud alerts are triggered.</p>
      </div>
    </div>

    <!-- Status filter -->
    <div class="card mb-4">
      <div class="flex flex-wrap gap-2">
        @for (filter of filters; track filter) {
          <button
            type="button"
            class="px-3 py-1.5 rounded-sm text-sm font-medium border border-[var(--fp-border)]"
            [class.fp-tab-active]="statusFilter() === filter"
            [class.fp-text-secondary]="statusFilter() !== filter"
            (click)="statusFilter.set(filter)"
          >
            {{ filter }}
          </button>
        }
      </div>
    </div>

    <!-- Case table -->
    <div class="card overflow-hidden">
      @if (filtered().length === 0) {
        <app-empty-state message="No cases match this filter" />
      } @else {
        <div class="overflow-auto">
          <table class="fp-table">
            <thead>
              <tr>
                <th>Case ID</th>
                <th>Title</th>
                <th>Transaction</th>
                <th>Status</th>
                <th>Risk</th>
                <th>Age</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              @for (c of filtered(); track c.id) {
                <tr>
                  <td><span class="fp-data-mono">{{ c.id }}</span></td>
                  <td>{{ c.title }}</td>
                  <td><span class="fp-data-mono">{{ c.transactionId }}</span></td>
                  <td><app-badge [value]="c.status" /></td>
                  <td><app-badge [value]="c.riskLevel" /></td>
                  <td>{{ c.createdAt | timeAgo }}</td>
                  <td>
                    <div class="flex flex-wrap items-center gap-2">
                      <button type="button" class="btn-secondary" (click)="view(c.id)">View</button>
                      @if (c.status === 'OPEN') {
                        <button type="button" class="btn-ghost" (click)="startInvestigation(c.id)">Investigate</button>
                      }
                    </div>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      }
    </div>
  `,
})
export class CaseListComponent implements OnInit {
  private caseService = inject(CaseService);
  private router = inject(Router);

  filters: CaseFilter[] = ['ACTIVE', 'ALL', 'OPEN', 'INVESTIGATING', 'CLOSED'];
  statusFilter = signal<CaseFilter>('ACTIVE');

  filtered = computed(() => {
    const filter = this.statusFilter();
    if (filter === 'ALL') return this.caseService.byStatus();
    if (filter === 'ACTIVE') {
      return this.caseService.cases().filter(c => c.status === 'OPEN' || c.status === 'INVESTIGATING');
    }
    return this.caseService.byStatus(filter as CaseStatus);
  });

  ngOnInit(): void {
    this.caseService.load();
  }

  view(id: string): void {
    this.router.navigate(['/cases', id]);
  }

  startInvestigation(id: string): void {
    this.caseService.updateStatus(id, 'INVESTIGATING');
  }
}