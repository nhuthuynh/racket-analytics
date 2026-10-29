// E2E-04-08 (ST-072b; FR-160; NFR-023; flows-sprint-04 §7 Q-10; api-sprint-04 §7 and §10): runs
// only in the `flags-on` project (PW_PROJECTS=flags-on) against a stack started with
// FEATURE_QUOTAS=1, nightly and by the verifier. Until that project exists in playwright.config.ts
// (ST-065 / ST-068b) the spec skips itself in every other project, so a flags-off stack never runs
// it. The limit is read from the API's own refusal, never assumed (PM-4 rule 2). The storage
// half (U-01) is ST-072b-part2.
import { expect, test, type APIRequestContext } from '@playwright/test';
import { expectNoBlockingA11yViolations, expectTargetsAtLeast24 } from '../../helpers/axe';
import { answerSetup, signInByLink } from '../../helpers/sprint-01';
import { PEOPLE } from '../../helpers/sprint-02';

async function newMatch(request: APIRequestContext, title: string) {
  return request.post('/api/matches', { data: { title, format: 'doubles', participants: PEOPLE } });
}

test.beforeEach(({}, testInfo) => {
  test.skip(testInfo.project.name !== 'flags-on', 'E2E-04-08 needs FEATURE_QUOTAS on (flags-on project)');
});

test.describe('E2E-04-08 Over-limit messages Q-10, match limit (flag on)', () => {
  test('E2E-04-08 Match limit: Q-07 says when a new match can start and keeps the answers, at 320 and 360 px', async ({ page }, testInfo) => {
    await page.setViewportSize({ width: 360, height: 740 });
    await signInByLink(page);
    let refused = false;
    for (let i = 0; i < 100 && !refused; i += 1) {
      const created = await newMatch(page.request, `Burst ${i + 1}`);
      refused = created.status() === 429;
      if (!refused) expect(created.status(), await created.text()).toBe(201);
    }
    expect(refused, 'the hourly match limit was never reached').toBe(true);
    await page.goto('/matches');
    await answerSetup(page, { format: 'Singles', players: ['Ivy', 'Carlos'], me: 'Ivy' });
    await page.getByRole('button', { name: 'Create match and upload' }).click();
    const alert = page.getByRole('alert').filter({ hasText: 'You can start a new match' });
    await expect(alert).toContainText(/You can start a new match (tomorrow )?at \d{2}:\d{2}\./);
    await expect(alert).toContainText('Your answers are kept.');
    await expect(page.getByRole('heading', { level: 1, name: 'Check your answers' })).toBeVisible();
    await expectNoBlockingA11yViolations(page, testInfo, 'Q-10-match-limit');
    await expectTargetsAtLeast24(page, testInfo, 'Q-10-match-limit');
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(360);
    // The same message at 320 px (G04-08 (a), (b), (d); QA-VERIFY04R3-06).
    await page.setViewportSize({ width: 320, height: 640 });
    await expect(alert).toContainText('Your answers are kept.');
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(320);
    await expectNoBlockingA11yViolations(page, testInfo, 'Q-10-match-limit-320');
    await expectTargetsAtLeast24(page, testInfo, 'Q-10-match-limit-320');
  });
});
