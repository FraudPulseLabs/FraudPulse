import { Component, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { AlertService } from '../../../core/services/alert.service';
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
        <p class="text-sm text-slate-500">Investigation workspace for linked alerts and transactions.</p>
      </div>
      <button type="button" class="btn-primary" (click)="showCreateForm.set(true)">New Case</button>
    </div>

    @if (showCreateForm()) {
      <div class="card mb-4">
        <h3 class="section-title">Create case</h3>
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <label>
            <span class="fp-label">Title</span>
            <input #titleInput class="fp-input" [value]="newCaseTitle()" (input)="newCaseTitle.set(titleInput.value)" />
          </label>
          <div>
            <span class="fp-label">Link alerts</span>
            <div class="max-h-56 overflow-auto rounded-lg border border-slate-200 p-3 space-y-2">
              @for (alert of newAlerts(); track alert.id) {
                <label class="flex items-start gap-2 text-sm">
                  <input type="checkbox" [checked]="selectedAlertIds().includes(alert.id)" (change)="toggleAlert(alert.id)" />
                  <span><span class="font-mono">{{ alert.id }}</span> - {{ alert.reason }}</span>
                </label>
              }
            </div>
          </div>
        </div>
        <div class="mt-4 flex flex-wrap items-center gap-3">
          <button type="button" class="btn-primary" (click)="createCase()">Create Case</button>
          <button type="button" class="btn-secondary" (click)="cancelCreate()">Cancel</button>
        </div>
      </div>
    }

    <div class="card mb-4">
      <div class="flex flex-wrap gap-2">
        @for (filter of filters; track filter) {
          <button
            type="button"
            class="px-3 py-1.5 rounded-lg text-sm font-medium border border-slate-200"
            [class.bg-indigo-600]="statusFilter() === filter"
            [class.text-white]="statusFilter() === filter"
            [class.text-slate-600]="statusFilter() !== filter"
            (click)="statusFilter.set(filter)"
          >
            {{ filter }}
          </button>
        }
      </div>
    </div>

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
                <th>Status</th>
                <th>Risk</th>
                <th>Alerts</th>
                <th>Age</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              @for (c of filtered(); track c.id) {
                <tr>
                  <td><span class="font-mono">{{ c.id }}</span></td>
                  <td>{{ c.title }}</td>
                  <td><app-badge [value]="c.status" /></td>
                  <td><app-badge [value]="c.riskLevel" /></td>
                  <td>{{ c.linkedAlertIds.length }}</td>
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
export class CaseListComponent {
  private caseService = inject(CaseService);
  private alertService = inject(AlertService);
  private router = inject(Router);

  filters: CaseFilter[] = ['ACTIVE', 'ALL', 'OPEN', 'INVESTIGATING', 'CLOSED'];
  statusFilter = signal<CaseFilter>('ACTIVE');
  showCreateForm = signal(false);
  newCaseTitle = signal('');
  selectedAlertIds = signal<string[]>([]);

  filtered = computed(() => {
    if (this.statusFilter() === 'ALL') return this.caseService.byStatus();
    if (this.statusFilter() === 'ACTIVE') {
      return this.caseService.cases().filter((c) => c.status === 'OPEN' || c.status === 'INVESTIGATING');
    }
    return this.caseService.byStatus(this.statusFilter() as CaseStatus);
  });

  newAlerts = computed(() => this.alertService.byStatus('NEW'));

  view(id: string): void {
    this.router.navigate(['/cases', id]);
  }

  startInvestigation(id: string): void {
    // TODO: PATCH /cases/:id { status: 'INVESTIGATING' }
    this.caseService.updateStatus(id, 'INVESTIGATING');
  }

  createCase(): void {
    if (!this.newCaseTitle().trim()) return;
    // TODO: validate at least one alert selected
    this.caseService.create(this.newCaseTitle(), this.selectedAlertIds());
    this.cancelCreate();
  }

  toggleAlert(id: string): void {
    this.selectedAlertIds.update((ids) => (ids.includes(id) ? ids.filter((item) => item !== id) : [...ids, id]));
  }

  cancelCreate(): void {
    this.showCreateForm.set(false);
    this.newCaseTitle.set('');
    this.selectedAlertIds.set([]);
  }
}
