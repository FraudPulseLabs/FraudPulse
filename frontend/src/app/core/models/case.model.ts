export type CaseStatus = 'OPEN' | 'INVESTIGATING' | 'CLOSED';
export type ResolutionCode = 'CONFIRMED_FRAUD' | 'FALSE_POSITIVE' | 'INCONCLUSIVE';
export type CaseEventType =
  | 'ALERT_ADDED'
  | 'STATUS_CHANGED'
  | 'NOTE_ADDED'
  | 'ASSIGNMENT_CHANGED'
  | 'RULE_TRIGGER';

export interface CaseNote {
  author: string;
  timestamp: string;
  body: string;
}

export interface CaseEvent {
  type: CaseEventType;
  timestamp: string;
  description: string;
  actor: string;
}

export interface FraudCase {
  id: string;
  title: string;
  status: CaseStatus;
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH';
  linkedAlertIds: string[];
  linkedTransactionIds: string[];
  resolutionCode?: ResolutionCode;
  assignedTo?: string;
  notes: CaseNote[];
  timeline: CaseEvent[];
  createdAt: string;
  updatedAt: string;
}
