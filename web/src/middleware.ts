// Per-request CSP nonce for HTML (ST-010; AQS/STACK-04). Next.js reads the nonce from the
// request's CSP header and applies it to its own scripts.
// The matcher skips /api/*: middleware would otherwise buffer request bodies, and tus PATCH
// bodies (8 MiB chunks, up to 64 MiB) must stream through the rewrite (api-sprint-00 §8).
import { NextResponse, type NextRequest } from 'next/server';
import { contentSecurityPolicy } from '@/lib/security/csp';

export function middleware(request: NextRequest) {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  const nonce = btoa(String.fromCharCode(...bytes));
  const csp = contentSecurityPolicy(nonce, { dev: process.env.NODE_ENV === 'development' });

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set('x-nonce', nonce);
  requestHeaders.set('Content-Security-Policy', csp);

  const response = NextResponse.next({ request: { headers: requestHeaders } });
  response.headers.set('Content-Security-Policy', csp);
  return response;
}

export const config = {
  matcher: [
    {
      source: '/((?!api/|_next/static|_next/image|sw.js|icons/|favicon.ico|manifest.webmanifest).*)',
    },
  ],
};
