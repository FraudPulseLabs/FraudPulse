import { Injectable } from '@angular/core';
import { caseStore } from '../mock/cases.mock';
import type { CaseNote, CaseStatus, FraudCase, ResolutionCode } from '../models';

@Injectable({ providedIn: 'root' })
export class CaseService {
  readonly cases = caseStore.asReadonly();

  byStatus(status?: CaseStatus): FraudCase[] {
    return status ? caseStore().filter((c) => c.status === status) : caseStore();
  }

  getById(id: string): FraudCase | undefined {
    return caseStore().find((c) => c.id === id);
  }

  create(title: string, alertIds: string[]): FraudCase {
    // TODO: POST /cases { title, alertIds }
    console.warn('[TODO] create case', title, alertIds);
    const now = new Date().toISOString();
    const newCase: FraudCase = {
      id: `CASE-${String(caseStore().length + 1).padStart(3, '0')}`,
      title,
      status: 'OPEN',
      riskLevel: 'HIGH',
      linkedAlertIds: alertIds,
      linkedTransactionIds: [],
      notes: [],
      timeline: [
        {
          type: 'ALERT_ADDED',
          timestamp: now,
          description: `Case created with ${alertIds.length} alert(s)`,
          actor: 'analyst@fraudpulse.demo',
        },
      ],
      createdAt: now,
      updatedAt: now,
    };
    caseStore.update((list) => [newCase, ...list]);
    return newCase;
  }

  updateStatus(id: string, status: CaseStatus, resolutionCode?: ResolutionCode): void {
    // TODO: PATCH /cases/:id { status, resolutionCode }
    console.warn('[TODO] update case status', id, status);
    const now = new Date().toISOString();
    caseStore.update((list) =>
      list.map((c) =>
        c.id === id
          ? {
              ...c,
              status,
              resolutionCode,
              updatedAt: now,
              timeline: [
                ...c.timeline,
                {
                  type: 'STATUS_CHANGED' as const,
                  timestamp: now,
                  description: `Status changed to ${status}${resolutionCode ? ` - ${resolutionCode}` : ''}`,
                  actor: 'analyst@fraudpulse.demo',
                },
              ],
            }
          : c,
      ),
    );
  }

  addNote(id: string, body: string): void {
    // TODO: POST /cases/:id/notes { body }
    console.warn('[TODO] add note to case', id);
    const now = new Date().toISOString();
    const note: CaseNote = {
      author: 'analyst@fraudpulse.demo',
      timestamp: now,
      body,
    };
    caseStore.update((list) =>
      list.map((c) =>
        c.id === id
          ? {
              ...c,
              notes: [...c.notes, note],
              updatedAt: now,
              timeline: [
                ...c.timeline,
                {
                  type: 'NOTE_ADDED' as const,
                  timestamp: now,
                  description: 'Note added',
                  actor: 'analyst@fraudpulse.demo',
                },
              ],
            }
          : c,
      ),
    );
  }

  assign(id: string, analyst: string): void {
    // TODO: PATCH /cases/:id { assignedTo: analyst }
    console.warn('[TODO] assign case', id, analyst);
    const now = new Date().toISOString();
    caseStore.update((list) =>
      list.map((c) =>
        c.id === id
          ? {
              ...c,
              assignedTo: analyst,
              updatedAt: now,
              timeline: [
                ...c.timeline,
                {
                  type: 'ASSIGNMENT_CHANGED' as const,
                  timestamp: now,
                  description: `Assigned to ${analyst}`,
                  actor: 'analyst@fraudpulse.demo',
                },
              ],
            }
          : c,
      ),
    );
  }
}
