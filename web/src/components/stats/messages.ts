// Load-failure words for D-01, E-01 and E-02 (flows-sprint-03 §2, §3 states; NFR-058): what
// happened, what to do, and the API's support reference when there is one. Never the raw error.
import { ApiError } from '@/lib/api/client';

export function loadProblem(e: unknown, what: string): string {
  if (e instanceof ApiError && e.code === 'network_error') {
    return `${what} could not be loaded because the connection dropped. Try again.`;
  }
  const ref = e instanceof ApiError && e.supportRef ? ` Reference: ${e.supportRef}` : '';
  return `${what} could not be loaded. Try again.${ref}`;
}

export function isStatus(e: unknown, status: number): boolean {
  return e instanceof ApiError && e.status === status;
}
