import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';
import { ToastService } from '../services/toast.service';

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const toast = inject(ToastService);

  return next(req).pipe(
    catchError(err => {
      const message = err.error?.['detail'] ?? err.message ?? 'Unexpected error';
      console.error(`[HTTP ${err.status}] ${message}`);

      const isAccessRequest = req.url.includes('/api/v1/access/');

      if (err.status === 401) {
        // Token missing/expired/invalid → drop the session and bounce to login.
        toast.error('Your session expired. Please sign in again.');
        void auth.signOut().finally(() => router.navigate(['/login']));
      } else if (err.status === 0) {
        if (!isAccessRequest) {
          toast.error('Cannot reach the server. Check your connection.');
        }
      } else if (!isAccessRequest) {
        toast.error(message);
      }

      return throwError(() => err);
    })
  );
};
