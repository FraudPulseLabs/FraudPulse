import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface AccessRequestPayload {
  email: string;
  company?: string;
  /** Honeypot value from the hidden field — always empty for real users. */
  website?: string;
}

export interface AccessRequestRecord {
  id: string;
  email: string;
  company: string | null;
  status: string;
  created_at: string;
}

interface AccessRequestResponse {
  success: boolean;
  message: string;
  data?: AccessRequestRecord | null;
}

interface AccessRequestListResponse {
  success: boolean;
  message: string;
  data: AccessRequestRecord[];
}

export interface AccessRequestApproveResponse {
  success: boolean;
  message: string;
  data?: AccessRequestRecord | null;
  /** One-time temporary password to relay to the user; null if already provisioned. */
  temp_password?: string | null;
}

@Injectable({ providedIn: 'root' })
export class AccessRequestService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/api/v1/access`;

  submit(payload: AccessRequestPayload): Observable<AccessRequestResponse> {
    return this.http.post<AccessRequestResponse>(`${this.baseUrl}/requests`, {
      email: payload.email.trim(),
      company: payload.company?.trim() || null,
      website: payload.website ?? '',
    });
  }

  list(): Observable<AccessRequestListResponse> {
    return this.http.get<AccessRequestListResponse>(`${this.baseUrl}/requests`);
  }

  approve(id: string): Observable<AccessRequestApproveResponse> {
    return this.http.post<AccessRequestApproveResponse>(
      `${this.baseUrl}/requests/${id}/approve`,
      {},
    );
  }
}

