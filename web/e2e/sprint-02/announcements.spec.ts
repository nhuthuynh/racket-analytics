// Binds tests/features/score_call.feature (QA-ACC for ST-029; FR-048 call format provisional,
// @needs-verification) and E2E-02-03: after each tag the polite live region says the rally
// number, the winner and the new score, and focus stays on the tagging controls (SC 4.1.3).
import { expect, test } from '@playwright/test';
import { JOURNEY, JOURNEY_ROWS, openTagging, receivedMatch, tagByKeys } from '../helpers/sprint-02';

test.describe('@M0 @story-ST-029 @needs-verification Score call and announcement', () => {
  test('E2E-02-03 each tag is announced in the live region and focus stays on the controls', async ({ page }) => {
    await openTagging(page, await receivedMatch(page));
    const region = page.locator('[role="status"][aria-live="polite"]').first();
    await expect(region).toHaveAttribute('aria-atomic', 'true');

    // Taps: focus stays on the ending button that saved the rally.
    const bar = page.getByRole('group', { name: 'Tag the rally' });
    await bar.getByRole('button', { name: 'Rally start' }).click();
    await page.waitForTimeout(5);
    await bar.getByRole('button', { name: 'Rally end' }).click();
    await bar.getByRole('button', { name: /^Your side/ }).click();
    await bar.getByRole('button', { name: 'Ivy', exact: true }).click();
    const winner = bar.getByRole('button', { name: 'Winner', exact: true });
    await winner.click();
    await expect(region).toHaveText(`Rally 1: us. Score ${JOURNEY_ROWS[0].score_after}.`);
    await expect(winner).toBeFocused();

    // Keys: the rest of the journey; focus never leaves the element that had it.
    const before = await page.evaluate(() => document.activeElement?.outerHTML ?? '');
    for (const [i, tag] of JOURNEY.slice(1).entries()) {
      const number = i + 2;
      await tagByKeys(page, tag, number);
      const row = JOURNEY_ROWS[number - 1]!;
      const who = row.winning_side === null ? 'replay' : row.winning_side === 'A' ? 'us' : 'them';
      await expect(region).toHaveText(`Rally ${number}: ${who}. Score ${row.score_after}.`);
      expect(await page.evaluate(() => document.activeElement?.outerHTML ?? '')).toBe(before);
    }
  });
});
