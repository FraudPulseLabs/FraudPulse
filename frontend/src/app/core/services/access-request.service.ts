import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface AccessRequestPayload {
  email: string;
  company?: string;
}

interface AccessRequestResponse {
  success: boolean;
  message: string;
}

@Injectable({ providedIn: 'root' })
export class AccessRequestService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/api/v1/access`;

  submit(payload: AccessRequestPayload): Observable<AccessRequestResponse> {
    return this.http.post<AccessRequestResponse>(`${this.baseUrl}/requests`, {
      email: payload.email.trim(),
      company: payload.company?.trim() || null,
    });
  }
}
