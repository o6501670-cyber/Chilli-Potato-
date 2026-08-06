import { of } from 'rxjs';

/** Test double that keeps component smoke tests offline and deterministic. */
export const mockApiService: any = new Proxy({}, {
  get: () => (..._args: unknown[]) => of([])
});
