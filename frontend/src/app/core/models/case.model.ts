// src/app/core/models/case.model.ts

export type CaseStatus = 'OPEN' | 'INVESTIGATING' | 'CLOSED';
export type CaseRiskLevel = 'LOW' | 'MEDIUM' | 'HIGH';
export type ResolutionCode = 'CONFIRMED_FRAUD' | 'FALSE_POSITIVE' | 'INCONCLUSIVE';
export type CaseEventType =
  | 'ALERT_ADDED'
  | 'STATUS_CHANGED'
  | 'NOTE_ADDED'
  | 'ASSIGNMENT_CHANGED'
  | 'RULE_TRIGGER';

export interface CaseNote {
  id: string;
  caseId: string;
  authorId: string;
  body: string;
  createdAt: string;
}

export interface CaseEvent {
  id: string;
  caseId: string;
  eventType: CaseEventType;
  description: string;
  actor: string;
  createdAt: string;
}

export interface FraudCase {
  id: string;
  transactionId: string;
  title: string;
  status: CaseStatus;
  riskLevel: CaseRiskLevel;
  resolutionCode?: ResolutionCode;
  assignedTo?: string;
  createdAt: string;
  updatedAt: string;
}

export interface CaseUpdate {
  status?: CaseStatus;
  riskLevel?: CaseRiskLevel;
  resolutionCode?: ResolutionCode;
  assignedTo?: string;
}