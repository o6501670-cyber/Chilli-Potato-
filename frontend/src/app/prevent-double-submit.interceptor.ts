import { HttpEvent, HttpHandlerFn, HttpInterceptorFn, HttpRequest } from '@angular/common/http';
import { Observable } from 'rxjs';
import { finalize, shareReplay } from 'rxjs/operators';

const inFlightRequests = new Map<string, Observable<HttpEvent<unknown>>>();

function serialiseBody(body: unknown): string | null {
  try {
    if (body instanceof FormData) {
      const entries: string[] = [];
      body.forEach((value, key) => {
        const encoded = value instanceof File
          ? `file:${value.name}:${value.size}:${value.lastModified}:${value.type}`
          : `text:${value}`;
        entries.push(`${key}=${encoded}`);
      });
      return entries.sort().join('&');
    }
    if (body instanceof Blob) {
      return `blob:${body.size}:${body.type}`;
    }
    return JSON.stringify(body ?? null);
  } catch {
    // A circular/custom body is unusual, but it must not break the request.
    return null;
  }
}

export const preventDoubleSubmitInterceptor: HttpInterceptorFn = (
  req: HttpRequest<unknown>,
  next: HttpHandlerFn
): Observable<HttpEvent<unknown>> => {
  if (req.method !== 'POST') {
    return next(req);
  }

  const bodyKey = serialiseBody(req.body);
  if (bodyKey === null) {
    return next(req);
  }
  const requestKey = `${req.method}_${req.urlWithParams}_${bodyKey}`;
  const existing = inFlightRequests.get(requestKey);
  if (existing) {
    return existing;
  }

  const shared$ = next(req).pipe(
    // Only concurrent duplicates are coalesced. Keeping a completed response in
    // the map caused legitimate repeated operations to receive stale data.
    finalize(() => inFlightRequests.delete(requestKey)),
    shareReplay({ bufferSize: 1, refCount: false }),
  );

  inFlightRequests.set(requestKey, shared$);
  return shared$;
};
