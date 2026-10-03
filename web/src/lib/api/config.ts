// Where server-side code reaches the API. Compose sets API_INTERNAL_URL=http://api:8000;
// PUBLIC_API_BASE_URL is the older name kept by infra/env.example (api-sprint-00 §9).
// Read by next.config at BUILD time for the /api rewrite, and at runtime by server components.
export const DEFAULT_API_INTERNAL_URL = 'http://api:8000';

export function apiInternalUrl(env: Record<string, string | undefined> = process.env): string {
  const raw = env.API_INTERNAL_URL || env.PUBLIC_API_BASE_URL || DEFAULT_API_INTERNAL_URL;
  const url = new URL(raw);
  if (url.protocol !== 'http:' && url.protocol !== 'https:') {
    throw new Error('API_INTERNAL_URL must be an http(s) URL');
  }
  return url.origin + url.pathname.replace(/\/+$/, '');
}
