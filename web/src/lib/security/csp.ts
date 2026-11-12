// Content-Security-Policy for HTML responses (ST-010; NFR-061; AQS/STACK-04).
// Scripts run only with the per-request nonce ('strict-dynamic' lets Next's own loader add
// chunks). No inline event handlers, no eval in production, no framing.

export function contentSecurityPolicy(nonce: string, { dev = false } = {}): string {
  if (!/^[A-Za-z0-9+/=_-]{16,}$/.test(nonce)) throw new Error('weak or malformed nonce');
  const directives: Record<string, string[]> = {
    'default-src': ["'self'"],
    'script-src': ["'self'", `'nonce-${nonce}'`, "'strict-dynamic'", ...(dev ? ["'unsafe-eval'"] : [])],
    'style-src': ["'self'", `'nonce-${nonce}'`, ...(dev ? ["'unsafe-inline'"] : [])],
    'img-src': ["'self'", 'data:', 'blob:'],
    'font-src': ["'self'"],
    'connect-src': ["'self'", ...(dev ? ['ws:', 'wss:'] : [])],
    'media-src': ["'self'", 'blob:'],
    'worker-src': ["'self'"],
    'manifest-src': ["'self'"],
    'object-src': ["'none'"],
    'base-uri': ["'self'"],
    'form-action': ["'self'"],
    'frame-ancestors': ["'none'"],
  };
  return Object.entries(directives)
    .map(([name, values]) => `${name} ${values.join(' ')}`)
    .join('; ');
}

/**
 * CSP for every answer the middleware does not see (NFR-050.7, ST-078e; IT-05-08): app files,
 * the service worker (its own CSP governs the worker's fetches, so same-origin stays allowed),
 * the manifest and icons. Nothing there is a document that runs inline code. Not /api/*: Next
 * adds no config header to an external rewrite's answer (measured 2026-11-05, IT-05-08), so the
 * API's own headers apply there (IT-00-14; decisions/ST-078e.md D3).
 */
export const STATIC_CONTENT_SECURITY_POLICY =
  "default-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'";

/** The paths src/middleware.ts skips (but /api/*), as next.config `headers()` sources. */
export const PATHS_WITHOUT_MIDDLEWARE = [
  '/_next/static/:path*',
  '/_next/image',
  '/sw.js',
  '/icons/:path*',
  '/favicon.ico',
  '/manifest.webmanifest',
] as const;
