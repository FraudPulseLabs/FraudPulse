// src/app/core/services/profile.service.ts
import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import type { Profile } from '../models/profile.model';

interface ProfileApiResponse {
  id: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

@Injectable({ providedIn: 'root' })
export class ProfileService {
  private http = inject(HttpClient);
  private baseUrl = `${environment.apiUrl}/api/v1/profiles`;

  private _analysts = signal<Profile[]>([]);
  readonly analysts = this._analysts.asReadonly();

  loadAnalysts(): void {
    this.http.get<ProfileApiResponse[]>(`${this.baseUrl}/analysts`).subscribe({
      next: (res) => this._analysts.set(res.map(this._map)),
      error: (err) => console.error('[ProfileService] loadAnalysts failed', err),
    });
  }

  private _map(raw: ProfileApiResponse): Profile {
    return {
      id:        raw.id,
      fullName:  raw.full_name,
      role:      raw.role as any,
      isActive:  raw.is_active,
      createdAt: raw.created_at,
    };
  }
}