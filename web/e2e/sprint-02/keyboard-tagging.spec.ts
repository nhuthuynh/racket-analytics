// Binds tests/features/keyboard_tagging.feature (QA-ACC for ST-028a; FR-051, NFR-034) and
// E2E-02-02: keyboard-only tagging of the 6-rally journey gives the same score sheet as tapping.
// Key map K-01 and single-key shortcuts that can be turned off (WCAG 2.1.4). Axe on T-01, K-01.
import { expect, test } from '@playwright/test';
import { expectNoBlockingA11yViolations, expectTargetsAtLeast24 } from '../helpers/axe';
import {
  JOURNEY,
  JOURNEY_ROWS,
  comparable,
  expectTaggingTargetsAtLeast48,
  journeyRows,
  openTagging,
  receivedMatch,
  sheetOf,
  tagByKeys,
  tagByTaps,
} from '../helpers/sprint-02';

test.describe('@M0 @story-ST-028 Keyboard tagging', () => {
  test('E2E-02-02 keyboard only gives the same score sheet as taps', async ({ page }, testInfo) => {
    test.slow(); // two matches, each uploaded and tagged

    const tapped = await receivedMatch(page, 'Tapped');
    await openTagging(page, tapped);
    await expectNoBlockingA11yViolations(page, testInfo, 'T-01');
    await expectTargetsAtLeast24(page, testInfo, 'T-01');
    await expectTaggingTargetsAtLeast48(page);
    for (const [i, tag] of JOURNEY.entries()) await tagByTaps(page, tag, i + 1);

    const keyed = await receivedMatch(page, 'Keyed', { signIn: false });
    await openTagging(page, keyed);
    // No pointer from here on: focus starts on the page body, every tag is keys only.
    await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
    for (const [i, tag] of JOURNEY.entries()) await tagByKeys(page, tag, i + 1);

    const byTaps = await sheetOf(page, tapped);
    const byKeys = await sheetOf(page, keyed);
    expect(journeyRows(byTaps)).toEqual(JOURNEY_ROWS);
    expect(comparable(byKeys)).toEqual(comparable(byTaps));
  });

  test('Show the key map', async ({ page }, testInfo) => {
    await openTagging(page, await receivedMatch(page));
    await page.keyboard.press('?');
    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();
    for (const words of ['Rally start', 'Rally end', 'Winner', 'Unforced error', 'Forced error', 'Fault', 'Replay', 'Undo']) {
      await expect(dialog.getByText(words, { exact: false }).first()).toBeVisible();
    }
    await expectNoBlockingA11yViolations(page, testInfo, 'K-01');
    await expectTargetsAtLeast24(page, testInfo, 'K-01');
    await page.keyboard.press('Escape');
    await expect(dialog).toBeHidden();
  });

  test('Turn single-key shortcuts off', async ({ page }) => {
    const matchId = await receivedMatch(page);
    await openTagging(page, matchId);
    await page.keyboard.press('?');
    const dialog = page.getByRole('dialog');
    await dialog.getByRole('checkbox').first().uncheck();
    await page.keyboard.press('Escape');
    await expect(dialog).toBeHidden();

    // "1" (winner: your side) while the video (or the page, when the video cannot play here)
    // has focus: no winner is chosen, so the side buttons stay unpressed.
    const video = page.locator('video');
    if (await video.count()) await video.focus();
    await page.keyboard.press('s');
    await page.keyboard.press('1');
    const bar = page.getByRole('group', { name: 'Tag the rally' });
    for (const button of await bar.getByRole('group', { name: 'Won by' }).getByRole('button').all()) {
      await expect(button).toHaveAttribute('aria-pressed', 'false');
    }
    await expect(bar.getByRole('button', { name: 'Rally start' })).toHaveAttribute('aria-pressed', 'false');
    expect((await sheetOf(page, matchId)).rows).toEqual([]);
  });
});
