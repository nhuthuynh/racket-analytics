// NFR-050.7 (ST-078e; IT-05-08): every path the middleware skips (so gets no nonce CSP) has the
// static CSP in next.config, but /api/*, whose answers are the API's own (decisions/ST-078e.md D3).
// The matcher must stay a literal in src/middleware.ts (Next reads it at build time), so this test
// keeps the two lists together.
import { describe, expect, it } from 'vitest';
import nextConfig from '../../next.config';
import { config } from '@/middleware';
import { PATHS_WITHOUT_MIDDLEWARE, STATIC_CONTENT_SECURITY_POLICY } from '@/lib/security/csp';

function skippedByMiddleware(): string[] {
  const source = (config.matcher[0] as { source: string }).source;
  const inner = /\(\?!(.+)\)\.\*\)$/.exec(source)![1]!;
  return inner.split('|').map((p) => `/${p.replace(/\/$/, '')}`);
}

describe('static CSP on what the middleware skips (NFR-050.7)', () => {
  it('names a source for every skipped path but /api', () => {
    const covered = PATHS_WITHOUT_MIDDLEWARE.map((s) => s.replace('/:path*', ''));
    expect(skippedByMiddleware().filter((p) => p !== '/api').sort()).toEqual([...covered].sort());
  });

  it('next.config sends the static CSP, with frame denial, on each of them', async () => {
    const rules = await nextConfig.headers!();
    for (const source of PATHS_WITHOUT_MIDDLEWARE) {
      const rule = rules.find((r) => r.source === source);
      expect(rule?.headers, source).toContainEqual({ key: 'Content-Security-Policy', value: STATIC_CONTENT_SECURITY_POLICY });
    }
    expect(STATIC_CONTENT_SECURITY_POLICY).toContain("frame-ancestors 'none'");
  });
});
