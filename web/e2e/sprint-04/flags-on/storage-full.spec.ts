// E2E-04-08 storage half (ST-072b-part2; FR-160; NFR-023; flows-sprint-04 §7 Q-10; api-sprint-04 §7 and §10): runs
// only in the `flags-on` project (PW_PROJECTS=flags-on) against a stack started with
// FEATURE_QUOTAS=1, nightly and by the verifier. Until that project exists in playwright.config.ts
// (ST-065 / ST-068b) the spec skips itself in every other project, so a flags-off stack never runs
// it. Limits are read from the API's own refusals, never assumed (PM-4 rule 2). The match-limit
// half is over-limit.spec.ts (ST-072b).
import { expect, test, type APIRequestContext } from '@playwright/test';
import { expectNoBlockingA11yViolations, expectTargetsAtLeast24 } from '../../helpers/axe';
import { answerSetup, signInByLink } from '../../helpers/sprint-01';
import { PEOPLE } from '../../helpers/sprint-02';

const TUS = { 'Tus-Resumable': '1.0.0' };
const SESSION_BYTES = 9_900_000_000; // under UPLOAD_MAX_BYTES (10 GB)

async function newMatch(request: APIRequestContext, title: string) {
  return request.post('/api/matches', { data: { title, format: 'doubles', participants: PEOPLE } });
}

test.beforeEach(({}, testInfo) => {
  test.skip(testInfo.project.name !== 'flags-on', 'E2E-04-08 needs FEATURE_QUOTAS on (flags-on project)');
});

test.describe('E2E-04-08 Over-limit messages Q-10, storage full (flag on)', () => {
  test('Storage full: U-01 says how much is used of the limit, at 320 px', async ({ page }, testInfo) => {
    await page.setViewportSize({ width: 320, height: 640 });
    await signInByLink(page);
    // Declared, never-sent upload sessions fill the storage to just under the limit.
    for (let i = 0, filled = false; i < 3 && !filled; i += 1) {
      const created = await newMatch(page.request, `Space ${i + 1}`);
      expect(created.status(), await created.text()).toBe(201);
      const uploads = `/api/matches/${String(((await created.json()) as { id: string }).id)}/uploads`;
      const full = await page.request.post(uploads, { headers: { ...TUS, 'Upload-Length': String(SESSION_BYTES) } });
      if (full.status() === 201) continue;
      const { error } = (await full.json()) as { error: { code: string; quota: { used_bytes: number; limit_bytes: number } } };
      expect(error.code).toBe('storage_quota_exceeded');
      const rest = error.quota.limit_bytes - error.quota.used_bytes - 1000;
      if (rest > 0) {
        const last = await page.request.post(uploads, { headers: { ...TUS, 'Upload-Length': String(rest) } });
        expect(last.status(), await last.text()).toBe(201);
      }
      filled = true;
    }
    await page.goto('/matches');
    await answerSetup(page, { format: 'Singles', players: ['Ivy', 'Carlos'], me: 'Ivy' });
    await page.getByRole('button', { name: 'Create match and upload' }).click();
    const alert = page.getByRole('alert').filter({ hasText: "This video won't fit in your storage." });
    await expect(alert).toBeVisible({ timeout: 15_000 });
    await expect(alert).toContainText(/You have used \d+(\.\d)? of \d+(\.\d)? GB\./);
    await expect(alert).toContainText('Nothing from this file was saved.');
    await expect(alert.getByRole('link', { name: /won't fit/ })).toHaveAttribute('href', '/matches');
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(320);
    await expectNoBlockingA11yViolations(page, testInfo, 'Q-10-storage');
    await expectTargetsAtLeast24(page, testInfo, 'Q-10-storage');
  });
});
