// Playwright (ST-004 harness, ST-010 journeys; AQS/STACK-03). Specs live in web/e2e/ (QA-owned).
// The stack must already be running: CI uses Compose, locally see web/README.md.
// Projects: Chromium and WebKit, the skeleton of the NFR-024 browser matrix.
import { defineConfig, devices } from '@playwright/test';
import { chromiumDevCertificateArgs, trustsDevCertificate } from './src/lib/security/dev-tls';

// https: the Compose stack is served by the web-tls proxy (ADR 0029).
const baseURL = process.env.BASE_URL ?? 'https://localhost:3000';
const projects = (process.env.PW_PROJECTS ?? 'chromium,webkit').split(',').map((p) => p.trim());

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0, // flaky tests are quarantined with an owner, never retried silently (NFR-074)
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : [['list']],
  timeout: 60_000,
  use: {
    baseURL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    // Caddy's internal dev CA only: loopback https origins (ADR 0029).
    ignoreHTTPSErrors: trustsDevCertificate(baseURL),
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], launchOptions: { args: chromiumDevCertificateArgs(baseURL) } },
    },
    { name: 'webkit', use: { ...devices['iPhone 13'] } },
  ].filter((p) => projects.includes(p.name)),
});
