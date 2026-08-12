import { HttpInterceptorFn, HttpRequest, HttpHandlerFn, HttpEvent } from '@angular/common/http';
import { Observable } from 'rxjs';
import { finalize, shareReplay } from 'rxjs/operators';

const inFlightRequests = new Map<string, Observable<HttpEvent<unknown>>>();

export const preventDoubleSubmitInterceptor: HttpInterceptorFn = (
  req: HttpRequest<unknown>,
  next: HttpHandlerFn
): Observable<HttpEvent<unknown>> => {
  // Only apply to POST requests (creations).
  if (req.method !== 'POST') {
    return next(req);
  }

  // Create a unique key for the request based on URL and body content
  const requestKey = `${req.method}_${req.url}_${JSON.stringify(req.body || {})}`;

  if (inFlightRequests.has(requestKey)) {
    console.warn(`Double-click duplicate request shared: ${req.url}`);
    return inFlightRequests.get(requestKey)!;
  }

  const shared$ = next(req).pipe(
    finalize(() => {
      // Remove it from the in-flight list after a delay to prevent spam clicks right after completion
      setTimeout(() => {
        inFlightRequests.delete(requestKey);
      }, 1000);
    }),
    shareReplay(1)
  );

  inFlightRequests.set(requestKey, shared$);
  return shared$;
};
