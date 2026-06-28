// src/app/core/models/profile.model.ts

export type UserRole = 'FRAUD_ANALYST' | 'CUSTOMER_SUPPORT' | 'SYSTEM_ADMIN';

export interface Profile {
  id: string;
  fullName: string;
  role: UserRole;
  isActive: boolean;
  createdAt: string;
}