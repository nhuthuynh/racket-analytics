// E2E-03-01 journey v2 (ST-054 QA; sprint-03 §6, §12 demo steps 1-3 and 6; Gherkin §7.1, §7.3,
// §7.5). A new player signs in by link, sets up a doubles match, uploads the 60 s fixture, tags
// the coach's worked example on T-01, and the stats equal the reference (n, value, low-sample
// text, unofficial notice); "Show me" on "Rallies won on serve" lists its 7 rallies and one
// plays; the match is deleted after a confirmation that names what goes, and it is gone.
// UI assumptions: e2e/helpers/sprint-03.ts (until PD-1/DR-03). Rules are provisional.
import { expect, test } from '@playwright/test';
import { expectNoBlockingA11yViolations, expectTargetsAtLeast24 } from '../helpers/axe';
import { answerSetup, createAndUpload, signInByLink } from '../helpers/sprint-01';
import { MY_SIDE, playableVideo } from '../helpers/sprint-02';
import {
  METRIC_NAMES, PUBLISHED, REFERENCE, SCREEN, UNOFFICIAL, expectSidePrinted, metricCard, statsPath,
  tagWorkedExampleOnT01,
} from '../helpers/sprint-03';

test.describe('@M0 @story-ST-054 @needs-verification Journey v2', { tag: '@red-until-ST-048' }, () => {
  test('E2E-03-01 tag the worked example, stats equal the reference, Show me plays, delete the match', async ({ page }, testInfo) => {
    test.setTimeout(240_000);
    expect(PUBLISHED.length, 'no coach-reviewed metric to show (COACH-1, FR-102)').toBeGreaterThan(0);

    await signInByLink(page);
    await answerSetup(page, { format: 'Doubles', players: ['Ivy', 'Dana', 'Carlos', 'Sam'], me: 'Ivy' });
    await createAndUpload(page);
    await expect(page.getByText('Video received')).toBeVisible({ timeout: 120_000 });
    const matchId = /\/matches\/([^/?#]+)/.exec(page.url())?.[1] ?? '';
    expect(matchId).not.toBe('');

    await playableVideo(page);
    await page.getByRole('link', { name: 'Tag rallies' }).click();
    await page.getByRole('radio', { name: MY_SIDE }).check();
    await page.getByRole('button', { name: 'Start game 1' }).click();
    await tagWorkedExampleOnT01(page, matchId);

    // D-01: the stats equal the reference, every shown metric for both sides
    await page.goto(statsPath(matchId));
    await expect(page.getByRole('heading', { level: 1 })).toContainText(/stats/i);
    await expect(page.getByText(UNOFFICIAL).first()).toBeVisible();
    for (const entry of PUBLISHED) {
      const card = metricCard(page, entry.id);
      await expect(card, `${entry.id} card`).toBeVisible();
      for (const side of ['A', 'B'] as const) await expectSidePrinted(card, entry.id, side);
    }
    await expectNoBlockingA11yViolations(page, testInfo, SCREEN.dashboard);
    await expectTargetsAtLeast24(page, testInfo, SCREEN.dashboard);

    // E-01: "Show me" on "Rallies won on serve" (Ivy's side) lists the 7 rallies; one plays
    const serve = metricCard(page, 'AN-01');
    await serve.getByRole('button', { name: /Show me/ }).first().click();
    const list = page.getByRole('list', { name: new RegExp(METRIC_NAMES['AN-01'] ?? '') });
    await expect(list.getByRole('listitem')).toHaveCount(REFERENCE['AN-01']?.A.rallies.length ?? -1);
    await expectNoBlockingA11yViolations(page, testInfo, SCREEN.evidence);
    await list.getByRole('link').first().click();
    await expect
      .poll(() => page.evaluate(() => { const v = document.querySelector('video'); return v ? v.readyState : -1; }), { timeout: 15_000 })
      .toBeGreaterThanOrEqual(2);

    // X-01: delete the match; the confirmation names what goes; afterwards it is gone
    await page.goto(`/matches/${matchId}`);
    await page.getByRole('button', { name: /Delete match/ }).click();
    const dialog = page.getByRole('dialog');
    for (const what of [/video/i, /tags/i, /score sheet/i, /stats/i, /cannot be (undone|restored)/i]) {
      await expect(dialog).toContainText(what);
    }
    await expectNoBlockingA11yViolations(page, testInfo, SCREEN.deleteMatch);
    await expectTargetsAtLeast24(page, testInfo, SCREEN.deleteMatch); // NFR-028 on X-01 too (PD-R1S3-03)
    const typed = dialog.getByRole('textbox');
    if (await typed.count()) await typed.fill('delete');
    await dialog.getByRole('button', { name: /Delete/ }).last().click();
    await expect(page).toHaveURL(/\/matches\/?(\?|#|$)/);
    await expect(page.getByText('Saturday doubles')).toHaveCount(0);
    expect((await page.request.get(`/api/matches/${matchId}`)).status()).toBe(404);
    expect((await page.request.get(`/api/matches/${matchId}/stats`)).status()).toBe(404);
  });
});
