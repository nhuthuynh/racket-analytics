// Next.js config (ST-010). Security headers on every response [AQS/STACK-04]; the CSP with a
// per-request nonce is set in src/middleware.ts. `/api/*` is proxied to the API so the browser
// stays same-origin (api-sprint-00 §1).
import type { NextConfig } from 'next';
import { apiInternalUrl } from './src/lib/api/config';

const securityHeaders = [
  { key: 'X-Content-Type-Options', value: 'nosniff' },
  { key: 'X-Frame-Options', value: 'DENY' },
  { key: 'Referrer-Policy', value: 'no-referrer' },
  { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=(), payment=()' },
  { key: 'Cross-Origin-Opener-Policy', value: 'same-origin' },
];

const nextConfig: NextConfig = {
  poweredByHeader: false,
  reactStrictMode: true,
  async headers() {
    return [
      { source: '/:path*', headers: securityHeaders },
      {
        // Caption files must carry their type: nosniff makes browsers refuse anything else.
        source: '/guide/capture-guide.en.vtt',
        headers: [{ key: 'Content-Type', value: 'text/vtt; charset=utf-8' }],
      },
      {
        // The service worker itself must always be revalidated so a fix reaches users.
        source: '/sw.js',
        headers: [
          { key: 'Cache-Control', value: 'no-cache, no-store, must-revalidate' },
          { key: 'Content-Type', value: 'application/javascript; charset=utf-8' },
        ],
      },
    ];
  },
  async rewrites() {
    return [{ source: '/api/:path*', destination: `${apiInternalUrl()}/:path*` }];
  },
};

export default nextConfig;
