import { HttpInterceptorFn } from '@angular/common/http';
import { catchError, throwError } from 'rxjs';

export const errorInterceptor: HttpInterceptorFn = (req, next) =>
  next(req).pipe(
    catchError(err => {
      const message = err.error?.['detail'] ?? err.message ?? 'Unexpected error';
      console.error(`[HTTP ${err.status}] ${message}`);
      return throwError(() => err);
    })
  );
