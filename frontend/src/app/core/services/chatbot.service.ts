import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface AssistantSource {
  number: number;
  title: string;
  filename: string;
  heading: string | null;
  score: number;
}

export interface AssistantResponse {
  answer: string;
  sources: AssistantSource[];
  grounded: boolean;
  refused: boolean;
  latency_ms: number;
  model: string | null;
}

/**
 * Talks to the backend RAG assistant. All knowledge now lives in the backend
 * corpus (`backend/rag/docs`); the frontend only sends the question and renders
 * the grounded, cited answer.
 */
@Injectable({ providedIn: 'root' })
export class ChatbotService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/api/v1/assistant`;

  ask(message: string): Observable<AssistantResponse> {
    return this.http.post<AssistantResponse>(`${this.baseUrl}/chat`, {
      message: message.trim(),
    });
  }
}
