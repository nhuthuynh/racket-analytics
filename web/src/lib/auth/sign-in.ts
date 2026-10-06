// Sign-in rules and copy (ST-013; flows-sprint-01 A-01..A-04; api-sprint-01 §2.1).
// Pure: no React, no I/O. Copy strings match the flows document and the Gherkin exactly.
import type { ApiError } from '@/lib/api/client';

export const EMAIL_FORMAT_MESSAGE = 'Enter an email address in the correct format, like name@example.com';
export const OFFLINE_SIGN_IN_MESSAGE = "You're offline. Connect to the internet to get a sign-in link.";
const SERVER_MESSAGE = 'Sorry, we could not send a link right now. Try again in a few minutes.';

/** The API's "well-formed" rule: after trim 3-254 characters, one @, no spaces, a dot in the domain. */
export function isWellFormedEmail(value: string): boolean {
  const email = value.trim();
  if (email.length < 3 || email.length > 254) return false;
  if (/\s/.test(email)) return false;
  const parts = email.split('@');
  if (parts.length !== 2) return false;
  const [local, domain] = parts as [string, string];
  return local.length > 0 && domain.includes('.') && !domain.startsWith('.') && !domain.endsWith('.');
}

/** "… at 14:32." in the viewer's local time (or `timeZone`), from the API's retry time. */
export function rateLimitMessage(retryAt: string | null, timeZone?: string): string {
  const at = retryAt ? new Date(retryAt) : null;
  if (!at || Number.isNaN(at.getTime())) {
    return 'You have asked for too many links. Try again in a few minutes.';
  }
  const time = new Intl.DateTimeFormat('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
    ...(timeZone ? { timeZone } : {}),
  }).format(at);
  return `You have asked for too many links. You can ask for a new link at ${time}.`;
}

/** The error-summary text for a failed link request. */
export function signInErrorMessage(error: ApiError): string {
  if (error.status === 0) return OFFLINE_SIGN_IN_MESSAGE;
  if (error.status === 422) return EMAIL_FORMAT_MESSAGE;
  if (error.status === 429) return rateLimitMessage(error.retryAt);
  return error.supportRef ? `${SERVER_MESSAGE} Reference: ${error.supportRef}` : SERVER_MESSAGE;
}
