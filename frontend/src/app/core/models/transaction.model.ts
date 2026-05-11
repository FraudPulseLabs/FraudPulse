export type Decision = 'ALLOW' | 'REVIEW' | 'BLOCK';
export type LifecycleStatus = 'AUTHORIZED' | 'SETTLED';

export interface ReasonCode {
  feature: string;
  direction: 'HIGH' | 'LOW';
  contribution: number;
}

export interface Transaction {
  id: string;
  userId: string;
  amount: number;
  currency: string;
  merchant: string;
  ts: string;
  userIp?: string;
  decision: Decision;
  score: number;
  modelVersion: string;
  lifecycleStatus: LifecycleStatus;
  reasons: ReasonCode[];
  isSimulated: boolean;
  isManual: boolean;
  caseId?: string;
}
