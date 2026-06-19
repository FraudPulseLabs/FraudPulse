import { inject } from '@angular/core';
import { CanMatchFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

/**
 * Gate the authenticated app shell. Awaits the persisted session so a hard
 * refresh on a protected route works, and redirects to the landing page when absent.
 */
export const authGuard: CanMatchFn = async () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const session = await auth.resolveSession();
  return session ? true : router.createUrlTree(['/']);
};

/**
 * Show the public landing page only to unauthenticated visitors.
 * Signed-in users are sent straight to the transactions workspace.
 */
export const guestGuard: CanMatchFn = async () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const session = await auth.resolveSession();
  return session ? router.createUrlTree(['/transactions']) : true;
};
