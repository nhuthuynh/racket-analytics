// CSP for HTML (IT-00-14 HTML part asserts default-src 'self' and frame-ancestors 'none').
import { describe, expect, it } from 'vitest';
import { contentSecurityPolicy } from '@/lib/security/csp';
import { apiInternalUrl } from '@/lib/api/config';

const NONCE = 'q1w2e3r4t5y6u7i8o9p0aa==';

describe('contentSecurityPolicy', () => {
  it('rejects a short or malformed nonce', () => {
    expect(() => contentSecurityPolicy('abc')).toThrow();
    expect(() => contentSecurityPolicy("x' 'unsafe-inline")).toThrow();
  });

  it('never allows unsafe-inline or unsafe-eval scripts in production', () => {
    const csp = contentSecurityPolicy(NONCE);
    const scriptSrc = csp.split('; ').find((d) => d.startsWith('script-src'))!;
    expect(scriptSrc).not.toContain('unsafe-inline');
    expect(scriptSrc).not.toContain('unsafe-eval');
    expect(scriptSrc).toContain(`'nonce-${NONCE}'`);
    expect(csp).not.toContain('unsafe-inline');
  });

  it('forbids framing and plugins and keeps everything same-origin by default', () => {
    const csp = contentSecurityPolicy(NONCE);
    expect(csp).toContain("default-src 'self'");
    expect(csp).toContain("frame-ancestors 'none'");
    expect(csp).toContain("object-src 'none'");
    expect(csp).toContain("connect-src 'self'");
  });

  it('allows eval only for the dev server', () => {
    expect(contentSecurityPolicy(NONCE, { dev: true })).toContain("'unsafe-eval'");
  });
});

describe('apiInternalUrl', () => {
  it('rejects a non-http URL', () => {
    expect(() => apiInternalUrl({ API_INTERNAL_URL: 'file:///etc/passwd' })).toThrow();
  });

  // The /api rewrite is resolved at `next build` (verified: `next start` ignores a changed
  // API_INTERNAL_URL), so the default must be the Compose address from api-sprint-00 §1.
  it('prefers API_INTERNAL_URL, then PUBLIC_API_BASE_URL, then the Compose API', () => {
    expect(apiInternalUrl({ API_INTERNAL_URL: 'http://api:8000/' })).toBe('http://api:8000');
    expect(apiInternalUrl({ PUBLIC_API_BASE_URL: 'http://localhost:8001' })).toBe(
      'http://localhost:8001',
    );
    expect(apiInternalUrl({})).toBe('http://api:8000');
  });
});
