import { HttpInterceptorFn, HttpRequest, HttpHandlerFn, HttpEvent } from '@angular/common/http';
import { Observable, EMPTY } from 'rxjs';
import { finalize } from 'rxjs/operators';

const inFlightRequests = new Set<string>();

export const preventDoubleSubmitInterceptor: HttpInterceptorFn = (
  req: HttpRequest<unknown>,
  next: HttpHandlerFn
): Observable<HttpEvent<unknown>> => {
  // Only apply to POST requests (creations). We can include PUT/PATCH if needed, but POST is the main issue for duplicate entries.
  if (req.method !== 'POST') {
    return next(req);
  }

  // Create a unique key for the request based on URL and body content
  const requestKey = `${req.method}_${req.url}_${JSON.stringify(req.body || {})}`;

  if (inFlightRequests.has(requestKey)) {
    console.warn(`Double-click duplicate request prevented: ${req.url}`);
    return EMPTY;
  }

  inFlightRequests.add(requestKey);

  return next(req).pipe(
    finalize(() => {
      // Remove it from the in-flight list after a delay to prevent spam clicks right after completion
      setTimeout(() => {
        inFlightRequests.delete(requestKey);
      }, 1000);
    })
  );
};
