/** Shape shared by `environment.ts` and `environment.development.ts`. */
export interface AppEnvironment {
  production: boolean;
  supabaseUrl: string;
  supabasePublicKey: string;
  apiUrl: string;
  useMock: boolean;
}
