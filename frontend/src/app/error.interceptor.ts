import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError } from 'rxjs/operators';
import { throwError } from 'rxjs';
import { ToastService } from './services/toast.service';

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const toastService = inject(ToastService);

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      let errorMsg = 'An unknown error occurred.';
      if (error.error instanceof ErrorEvent) {
        // Client side error
        errorMsg = `Error: ${error.error.message}`;
      } else {
        // Server side error
        if (error.status === 0) {
          errorMsg = 'Cannot connect to the server. Please check your internet connection.';
        } else if (error.status >= 500) {
          errorMsg = 'Server Error: We are looking into it. Please try again later.';
        } else if (error.status === 403) {
          errorMsg = 'You do not have permission to perform this action.';
        } else if (error.status === 400 && error.error) {
          // Attempt to extract validation messages from Django DRF
          const msgs = [];
          if (typeof error.error === 'object') {
             for (const key in error.error) {
                 if (Array.isArray(error.error[key])) {
                     msgs.push(`${key}: ${error.error[key][0]}`);
                 } else {
                     msgs.push(error.error[key]);
                 }
             }
             errorMsg = msgs.join(', ') || 'Validation error.';
          } else {
              errorMsg = error.error;
          }
        }
      }
      
      toastService.showError(errorMsg);
      return throwError(() => error);
    })
  );
};
