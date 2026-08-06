import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const router = inject(Router);
  const token = localStorage.getItem('token');

  let headers = req.headers
    .set('Cache-Control', 'no-cache, no-store, must-revalidate')
    .set('Pragma', 'no-cache')
    .set('Expires', '0');

  // Do not attach token for login requests
  if (token && !req.url.includes('/login/')) {
    headers = headers.set('Authorization', `Token ${token}`);
  }

  req = req.clone({ headers });

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      // FIXED: If the server returns 401 (token invalid/expired/deleted),
      // clear local storage and redirect to login automatically.
      if (error.status === 401) {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        router.navigate(['/login']);
      }
      return throwError(() => error);
    })
  );
};
