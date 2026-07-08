import { inject } from '@angular/core';
import { CanActivateFn, CanMatchFn, Router } from '@angular/router';
import { ADMIN_EMAIL, AuthService } from '../services/auth.service';

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
 * Signed-in users are sent straight to the operations overview.
 */
export const guestGuard: CanMatchFn = async () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const session = await auth.resolveSession();
  return session ? router.createUrlTree(['/overview']) : true;
};

/**
 * Restrict a route to the single admin account (access-request administration).
 * Non-admins are redirected to the operations overview.
 */
export const adminGuard: CanActivateFn = async () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const session = await auth.resolveSession();
  const email = session?.user?.email?.toLowerCase() ?? '';
  return email === ADMIN_EMAIL ? true : router.createUrlTree(['/overview']);
};
