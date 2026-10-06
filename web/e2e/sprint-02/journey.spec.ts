// E2E-02-01 journey v1 (ST-039 slice 1; sprint-02 §6, §12; QD §7 first half): a new player signs
// in by link, sets up a doubles match, uploads the 60 s fixture, tags 6 rallies on Quick Tag by
// taps, and the score sheet equals the golden sheet, with the unofficial label (FR-049, FR-050,
// FR-055; ADR 0009, ADR 0023). Everything goes through the UI; only the final sheet comparison
// also reads the API so the golden rows are compared field by field.
import { expect, test } from '@playwright/test';
import { expectNoBlockingA11yViolations, expectTargetsAtLeast24 } from '../helpers/axe';
import { answerSetup, createAndUpload, signInByLink } from '../helpers/sprint-01';
import {
  JOURNEY,
  JOURNEY_ROWS,
  MY_SIDE,
  UNOFFICIAL,
  expectTaggingTargetsAtLeast48,
  journeyRows,
  sheetOf,
  tagByTaps,
} from '../helpers/sprint-02';

const SERVER: Record<string, string> = { A: 'Your side', B: 'Other side' };

test.describe('@M0 @story-ST-039 Journey v1', () => {
  test('E2E-02-01 sign in, set up, upload, Quick Tag 6 rallies, the sheet equals the golden sheet', async ({ page }, testInfo) => {
    test.slow(); // upload and probe of the fixture, then 6 tags

    // Sign in with a magic link, as a new player (rule 10: a fresh account)
    await signInByLink(page);

    // Set up a doubles match and upload the fixture
    await answerSetup(page, { format: 'Doubles', players: ['Ivy', 'Dana', 'Carlos', 'Sam'], me: 'Ivy' });
    await createAndUpload(page);
    await expect(page.getByText('Video received')).toBeVisible({ timeout: 120_000 });
    const matchId = /\/matches\/([^/?#]+)/.exec(page.url())?.[1] ?? '';
    expect(matchId, `match id in ${page.url()}`).not.toBe('');

    // Quick Tag from the match page
    await page.getByRole('link', { name: 'Tag rallies' }).click();
    await expect(page.getByRole('heading', { level: 1, name: 'Tag rallies' })).toBeVisible();
    await page.getByRole('radio', { name: MY_SIDE }).check();
    await page.getByRole('button', { name: 'Start game 1' }).click();
    await expect(page.getByRole('group', { name: 'Tag the rally' })).toBeVisible();
    await expectNoBlockingA11yViolations(page, testInfo, 'T-01-journey');
    await expectTargetsAtLeast24(page, testInfo, 'T-01-journey');
    await expectTaggingTargetsAtLeast48(page);
    for (const [i, tag] of JOURNEY.entries()) await tagByTaps(page, tag, i + 1);

    // Open the score sheet from Quick Tag
    await page.getByRole('link', { name: 'Score sheet', exact: true }).click();
    await expect(page).toHaveURL(new RegExp(`/matches/${matchId}/sheet`));
    await expect(page.getByText(UNOFFICIAL, { exact: true })).toBeVisible();
    const table = page.getByRole('table', { name: 'Game 1' });
    await expect(table).toBeVisible();
    for (const row of JOURNEY_ROWS) {
      const cells = table.getByRole('row', { name: new RegExp(`Rally ${row.number}\\b`) }).getByRole('cell');
      await expect(cells.nth(1)).toContainText(SERVER[row.serving_side] ?? '');
      await expect(cells.nth(2)).toHaveText(row.score_before);
      await expect(cells.nth(3)).toHaveText(row.score_after);
    }
    await expectNoBlockingA11yViolations(page, testInfo, 'S-01-journey');

    // The sheet the server computes equals the golden rows (taglib reference stepper)
    const sheet = await sheetOf(page, matchId);
    expect(journeyRows(sheet)).toEqual(JOURNEY_ROWS);
    expect(sheet.unofficial).toBe(true);
    expect(sheet.label).toBe(UNOFFICIAL);
  });
});
