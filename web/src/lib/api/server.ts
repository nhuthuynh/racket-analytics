// The API client for server components: calls the API directly (API_INTERNAL_URL) and
// forwards only the session cookie of the incoming request (api-sprint-00 §2).
import { cookies } from 'next/headers';
import { cache } from 'react';
import { createApiClient } from './client';
import { apiInternalUrl } from './config';

const SESSION_COOKIES = ['__Host-racket_session', 'racket_session'] as const;

export async function serverApi() {
  const jar = await cookies();
  const cookie = SESSION_COOKIES.flatMap((name) => {
    const c = jar.get(name);
    return c ? [`${c.name}=${c.value}`] : [];
  }).join('; ');
  return createApiClient({
    baseUrl: apiInternalUrl(),
    headers: cookie ? { cookie } : {},
  });
}

/** One GET per request even when both the page and its metadata need the match. */
export const getMatchForRequest = cache(async (id: string) => (await serverApi()).getMatch(id));
