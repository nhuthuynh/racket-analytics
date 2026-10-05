// ADR 0029: the dev/E2E stack is served over https by Caddy's internal CA (infra/tls), which
// no browser trusts. Playwright may ignore certificate errors only for a loopback https origin;
// any other host keeps full certificate checks.
const LOOPBACK_HOSTS = new Set(['localhost', '127.0.0.1', '[::1]']);

export function trustsDevCertificate(baseURL: string): boolean {
  let url: URL;
  try {
    url = new URL(baseURL);
  } catch {
    return false;
  }
  return (
    url.protocol === 'https:' &&
    !url.username &&
    !url.password &&
    LOOPBACK_HOSTS.has(url.hostname)
  );
}

// Chromium will not register a service worker on an origin with a certificate error, even
// with Playwright's ignoreHTTPSErrors, so the dev origin also needs the browser-level flag.
export function chromiumDevCertificateArgs(baseURL: string): string[] {
  return trustsDevCertificate(baseURL) ? ['--ignore-certificate-errors'] : [];
}
