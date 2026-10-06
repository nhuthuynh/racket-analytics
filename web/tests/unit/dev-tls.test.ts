// ADR 0029: the dev/E2E stack is served by Caddy's internal CA, so Playwright may ignore
// certificate errors, but only for a loopback https origin, never for a real host.
import { describe, expect, it } from 'vitest';
import {
  chromiumDevCertificateArgs,
  trustsDevCertificate,
} from '@/lib/security/dev-tls';

describe('trustsDevCertificate', () => {
  it.each([
    'https://localhost.attacker.example',
    'https://localhost@attacker.example',
    'https://staging.racket.example',
    'http://localhost:3000',
    'https://127.0.0.2:3000',
    'not a url',
    '',
  ])('refuses %s', (url) => {
    expect(trustsDevCertificate(url)).toBe(false);
  });

  it.each([
    'https://localhost:3000',
    'https://localhost',
    'https://127.0.0.1:3000',
    'https://[::1]:3000',
  ])('accepts the loopback https origin %s', (url) => {
    expect(trustsDevCertificate(url)).toBe(true);
  });
});

// Chromium refuses to register a service worker on an origin with a certificate error even
// when Playwright ignores HTTPS errors ('An SSL certificate error occurred when fetching the
// script', measured 2026-10-05), so the offline sign-out journey needs the launch flag too.
describe('chromiumDevCertificateArgs', () => {
  it('adds nothing for a real host or plain http', () => {
    expect(
      chromiumDevCertificateArgs('https://localhost.attacker.example'),
    ).toEqual([]);
    expect(
      chromiumDevCertificateArgs('https://staging.racket.example'),
    ).toEqual([]);
    expect(chromiumDevCertificateArgs('http://localhost:3000')).toEqual([]);
  });

  it('ignores certificate errors for the loopback dev origin', () => {
    expect(chromiumDevCertificateArgs('https://localhost:3000')).toEqual([
      '--ignore-certificate-errors',
    ]);
  });
});
