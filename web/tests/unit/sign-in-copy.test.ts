// A-01..A-04 rules and copy (ST-013; flows-sprint-01 §2; api-sprint-01 §2.1). Pure functions.
import { describe, expect, it } from 'vitest';
import { isWellFormedEmail, rateLimitMessage, signInErrorMessage } from '@/lib/auth/sign-in';
import { ApiError } from '@/lib/api/client';

describe('isWellFormedEmail (same rule as the API, api-sprint-01 §2.1)', () => {
  it.each(['', '  ', 'ivy', 'ivy@', '@example.com', 'ivy@example', 'i v@example.com', 'a@b@c.com', 'a@.'])(
    'refuses %j',
    (value) => expect(isWellFormedEmail(value)).toBe(false),
  );

  it('refuses more than 254 characters', () => {
    expect(isWellFormedEmail(`${'a'.repeat(250)}@b.co`)).toBe(false);
  });

  it.each(['ivy@example.com', '  ivy+1@example.co.uk ', 'a@b.c'])('accepts %j', (value) =>
    expect(isWellFormedEmail(value)).toBe(true),
  );
});

describe('rateLimitMessage', () => {
  it('names the local, absolute time from the retry time', () => {
    expect(rateLimitMessage('2026-10-05T14:32:00Z', 'UTC')).toBe(
      'You have asked for too many links. You can ask for a new link at 14:32.',
    );
    expect(rateLimitMessage('2026-10-05T09:05:00Z', 'UTC')).toMatch(/at 09:05\.$/);
  });

  it('falls back to a time-free message without a retry time', () => {
    expect(rateLimitMessage(null)).toBe('You have asked for too many links. Try again in a few minutes.');
  });
});

describe('signInErrorMessage', () => {
  it('uses the format hint for a validation refusal', () => {
    expect(signInErrorMessage(new ApiError(422, 'validation_failed'))).toBe(
      'Enter an email address in the correct format, like name@example.com',
    );
  });

  it('says offline for a network failure', () => {
    expect(signInErrorMessage(new ApiError(0, 'network_error'))).toBe(
      "You're offline. Connect to the internet to get a sign-in link.",
    );
  });

  it('gives the support reference for a server problem, never internals', () => {
    expect(signInErrorMessage(new ApiError(500, 'internal_error', 'ref_5c1e0f3a9b7d4e21'))).toBe(
      'Sorry, we could not send a link right now. Try again in a few minutes. Reference: ref_5c1e0f3a9b7d4e21',
    );
    expect(signInErrorMessage(new ApiError(502, 'unknown'))).toBe(
      'Sorry, we could not send a link right now. Try again in a few minutes.',
    );
  });
});
