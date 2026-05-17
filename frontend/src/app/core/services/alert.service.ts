import { Injectable } from '@angular/core';
import { alertStore } from '../mock/alerts.mock';
import type { Alert, AlertStatus } from '../models';

@Injectable({ providedIn: 'root' })
export class AlertService {
  readonly alerts = alertStore.asReadonly();

  byStatus(status?: AlertStatus): Alert[] {
    return status ? alertStore().filter((a) => a.status === status) : alertStore();
  }

  getById(id: string): Alert | undefined {
    return alertStore().find((a) => a.id === id);
  }

  acknowledge(id: string): void {
    // TODO: PATCH /alerts/:id { status: 'ACKNOWLEDGED' }
    console.warn('[TODO] acknowledge alert', id);
    alertStore.update((list) =>
      list.map((a) =>
        a.id === id
          ? { ...a, status: 'ACKNOWLEDGED' as const, acknowledgedAt: new Date().toISOString() }
          : a,
      ),
    );
  }

  resolve(id: string, note: string): void {
    // TODO: PATCH /alerts/:id { status: 'RESOLVED', resolutionNote }
    console.warn('[TODO] resolve alert', id, note);
    alertStore.update((list) =>
      list.map((a) =>
        a.id === id
          ? {
              ...a,
              status: 'RESOLVED' as const,
              resolvedAt: new Date().toISOString(),
              resolutionNote: note,
            }
          : a,
      ),
    );
  }

  linkToCase(alertId: string, caseId: string): void {
    // TODO: PATCH /alerts/:id { caseId }
    console.warn('[TODO] link alert to case', alertId, caseId);
    alertStore.update((list) => list.map((a) => (a.id === alertId ? { ...a, caseId } : a)));
  }
}
