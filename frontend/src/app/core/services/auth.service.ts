import { Injectable, computed, inject, signal } from '@angular/core';
import type { AuthChangeEvent, Session, User } from '@supabase/supabase-js';
import { SupabaseService } from './supabase.service';

/**
 * Thin wrapper over Supabase Auth (GoTrue). Supabase owns users, passwords and
 * token issuance; this service exposes the current session as signals, signs in
 * and out, and surfaces the access token for the HTTP interceptor.
 *
 * supabase-js persists and auto-refreshes the session in localStorage, emitting
 * onAuthStateChange whenever it changes — we mirror that into a signal.
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly supabase = inject(SupabaseService).client;

  private readonly _session = signal<Session | null>(null);

  readonly session = this._session.asReadonly();
  readonly user = computed<User | null>(() => this._session()?.user ?? null);
  readonly isAuthenticated = computed(() => this._session() !== null);

  constructor() {
    // Hydrate from any persisted session, then stay in sync with refreshes.
    void this.supabase.auth.getSession().then(({ data }) => this._session.set(data.session));
    this.supabase.auth.onAuthStateChange((_event: AuthChangeEvent, session: Session | null) => {
      this._session.set(session);
    });
  }

  /** Current access token (JWT) for `Authorization: Bearer`, or null. */
  accessToken(): string | null {
    return this._session()?.access_token ?? null;
  }

  /**
   * Resolve the session from storage (await-able). Used by the route guard on
   * first load, before the async hydration in the constructor has settled.
   */
  async resolveSession(): Promise<Session | null> {
    const { data } = await this.supabase.auth.getSession();
    this._session.set(data.session);
    return data.session;
  }

  async signIn(email: string, password: string): Promise<void> {
    const { data, error } = await this.supabase.auth.signInWithPassword({ email, password });
    if (error) throw error;
    this._session.set(data.session);
  }


  async signOut(): Promise<void> {
    // Clear local session immediately so navigation/guards don't get stuck on network failures.
    this._session.set(null);
    try {
      await this.supabase.auth.signOut();
    } catch {
      // Best-effort remote sign-out (session already cleared locally).
    }
  }
}
