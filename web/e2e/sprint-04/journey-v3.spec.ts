// E2E-04-01 journey v3 (ST-065; QD §7; tests/features/e2e_journey.feature "Upload to plan").
// A new player signs in by link, sets up a doubles match, uploads the 60 s fixture, Quick Tags the
// coach's worked example on T-01, reads the score sheet and the stats, asks for a plan on P-02,
// and on P-01: a drill's "why" shows the metric, value and n of the independent reference
// (worked-example.reference.json), "Show me" lists the rallies behind it, a session is marked done
// offline (context.setOffline) and syncs back online, and "Not for me" swaps a drill.
// UI words: e2e/helpers/sprint-04.ts (flows-sprint-04 §2-§4). Rules are provisional.
import { expect, test } from '@playwright/test';
import { expectNoBlockingA11yViolations, expectTargetsAtLeast24 } from '../helpers/axe';
import { answerSetup, createAndUpload, signInByLink } from '../helpers/sprint-01';
import { MY_SIDE, playableVideo } from '../helpers/sprint-02';
import {
  REFERENCE, WORKED_EXAMPLE, expectSidePrinted, metricCard, pct, statsPath, tagWorkedExampleOnT01,
} from '../helpers/sprint-03';
import {
  CITED, PLAN_COPY, SCREEN_P, SWAPPABLE, answerPlanSetup, drillRow, planRead, sessionOf, whyOf,
} from '../helpers/sprint-04';

test.describe('@M0 @story-ST-065 @needs-verification Journey v3', () => {
  test('E2E-04-01 Upload to plan: Quick Tag, score sheet, stats, plan, why, Show me, done offline, swap', async ({ page, context }, testInfo) => {
    test.setTimeout(300_000);

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

    // S-01: every tagged rally is on the score sheet
    await page.goto(`/matches/${matchId}/sheet`);
    const sheet = page.getByRole('table', { name: 'Game 1' });
    await expect(sheet.getByRole('row', { name: /^Rally \d+/ })).toHaveCount(WORKED_EXAMPLE.length);

    // D-01: the cited metric equals the reference; its link leads to P-01
    await page.goto(statsPath(matchId));
    await expectSidePrinted(metricCard(page, 'AN-02'), 'AN-02', 'A');
    await page.getByRole('link', { name: 'Your training plan' }).click();
    await expect(page.getByRole('heading', { level: 1, name: 'Your training plan' })).toBeVisible();

    // P-01 empty → P-02 → P-01 with the plan
    await expect(page.getByText(PLAN_COPY.noPlan)).toBeVisible();
    await page.getByRole('link', { name: 'Make my plan' }).click();
    await answerPlanSetup(page);
    await page.getByRole('button', { name: 'Make my plan' }).click();
    await expect(page).toHaveURL(/\/plan(\?|#|$)/);
    await expect(page.getByRole('heading', { level: 2, name: 'Your sessions' })).toBeVisible();

    // FR-122: every drill's why reads "<metric>: <value> of|over <n>"; the cited one equals the reference
    const rows = page.locator('li[id^="drill-"]');
    const count = await rows.count();
    expect(count).toBeGreaterThan(0);
    for (let i = 0; i < count; i++) expect(await whyOf(rows.nth(i)), `drill row ${i + 1}`).not.toBeNull();
    const ref = REFERENCE['AN-02']?.A;
    expect(await whyOf(drillRow(page, CITED))).toEqual({ metric: 'Rallies won when receiving', value: pct(ref?.value ?? null), n: ref?.n });
    await expectNoBlockingA11yViolations(page, testInfo, SCREEN_P.plan);
    await expectTargetsAtLeast24(page, testInfo, SCREEN_P.plan);

    // "Show me": the rallies behind the cited value
    await drillRow(page, CITED).getByRole('button', { name: /^Show me the rallies behind Rallies won when receiving/ }).click();
    const list = drillRow(page, CITED).getByRole('list', { name: /Rallies won when receiving/ });
    await expect(list.getByRole('listitem')).toHaveCount(ref?.rallies.length ?? -1);

    // P-03: mark session 1 done offline; it syncs back online
    await context.setOffline(true);
    const first = sessionOf(page, 1);
    await expect(drillRow(page, SWAPPABLE).getByText(PLAN_COPY.needsConnection)).toBeVisible();
    await first.getByRole('button', { name: 'Mark done' }).click();
    await expect(first.getByText(PLAN_COPY.queued)).toBeVisible();
    await context.setOffline(false);
    await expect(page.getByRole('status').filter({ hasText: PLAN_COPY.synced(1) })).toBeVisible({ timeout: 15_000 });
    await expect(first.getByText('Done', { exact: true })).toBeVisible();
    expect((await planRead(page)).sessions[0]?.done).toBe(true);

    // P-03: "Not for me" swaps a drill; the new one has focus and is named in the status
    const row = drillRow(page, SWAPPABLE);
    await row.getByRole('button', { name: `Not for me, ${SWAPPABLE}` }).click();
    const dialog = page.getByRole('dialog', { name: `Swap ${SWAPPABLE}?` });
    await expect(dialog.getByRole('button', { name: 'Cancel' })).toBeFocused();
    await dialog.getByLabel('Why not? (optional)').fill('Too hard on my wrist');
    await expectNoBlockingA11yViolations(page, testInfo, SCREEN_P.swap);
    await dialog.getByRole('button', { name: 'Swap drill' }).click();
    const swapped = page.getByRole('status').filter({ hasText: /^Swapped for .+\.$/ });
    await expect(swapped).toBeVisible();
    const newName = /^Swapped for (.+)\.$/.exec((await swapped.textContent()) ?? '')?.[1] ?? '';
    expect(newName).not.toBe(SWAPPABLE);
    await expect(page.locator('li[id^="drill-"]:focus')).toContainText(newName);
  });
});
