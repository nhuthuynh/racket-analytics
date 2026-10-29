// Playwright (ST-004 harness, ST-010 journeys; AQS/STACK-03). Specs live in web/e2e/ (QA-owned).
// The stack must already be running: CI uses Compose, locally see web/README.md.
// Projects: Chromium and WebKit, the skeleton of the NFR-024 browser matrix. On CI the
// "chromium" project launches Google Chrome, which decodes the H.264 match video (QA-RV1-07,
// SRE-S2-05; e2e/helpers/browser-channel.ts). "flags-on" (ST-065, PE-4 §10) runs only the
// e2e/sprint-04/flags-on/ specs, only when PW_PROJECTS names it (e2e/helpers/projects.ts).
import { defineConfig } from '@playwright/test';
import { chromiumChannel } from './e2e/helpers/browser-channel';
import { e2eProjects, projectNames } from './e2e/helpers/projects';
import { chromiumDevCertificateArgs, trustsDevCertificate } from './src/lib/security/dev-tls';

// https: the Compose stack is served by the web-tls proxy (ADR 0029).
const baseURL = process.env.BASE_URL ?? 'https://localhost:3000';
const channel = chromiumChannel(process.env);

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
  projects: e2eProjects({ names: projectNames(process.env), channel, chromiumArgs: chromiumDevCertificateArgs(baseURL) }),
});
