// Binds tests/features/score_sheet.feature in the browser (QA-ACC for ST-030; FR-049, FR-055;
// NFR-033, NFR-034): every rally readable as text, the unofficial label on every sheet, and no
// sideways scrolling at 320 and 360 px (viewport matrix 320/360/768/1280, G02-10 (d)).
import { expect, test } from '@playwright/test';
import { expectNoBlockingA11yViolations, expectTargetsAtLeast24 } from '../helpers/axe';
import { UNOFFICIAL, expectNoSidewaysScroll, receivedMatch, tagJourneyByApi } from '../helpers/sprint-02';

test.describe('@M0 @story-ST-030 Score sheet', () => {
  test('Read the match without the video', async ({ page }, testInfo) => {
    const matchId = await receivedMatch(page);
    await tagJourneyByApi(page, matchId);
    await page.goto(`/matches/${matchId}/sheet`);
    const table = page.getByRole('table', { name: 'Game 1' });
    await expect(table).toBeVisible();
    for (const header of ['Rally', 'Server', 'Score before', 'Score after', 'Won by', 'Ending', 'Player']) {
      await expect(table.getByRole('columnheader', { name: header, exact: true })).toBeVisible();
    }
    const row2 = table.getByRole('row', { name: /Rally 2/ });
    await expect(row2.getByRole('cell').nth(1)).toHaveText('Your side, server 2');
    await expect(row2.getByRole('cell').nth(2)).toHaveText('1-0-2');
    await expect(row2.getByRole('cell').nth(3)).toHaveText('0-1-1');
    await expect(row2.getByRole('cell').nth(4)).toHaveText('Other side');
    await expect(row2.getByRole('cell').nth(5)).toHaveText('Unforced error');
    await expect(row2.getByRole('cell').nth(6)).toHaveText('player not tagged'); // quick_tag "Responsible player skipped"
    await expect(table.getByRole('row', { name: /Rally 5/ }).getByRole('cell').nth(4)).toHaveText('No one (replay)');
    await expectNoBlockingA11yViolations(page, testInfo, 'S-01');
    await expectTargetsAtLeast24(page, testInfo, 'S-01');
  });

  test('Rules not yet verified', async ({ page }) => {
    const matchId = await receivedMatch(page);
    await page.goto(`/matches/${matchId}/sheet`);
    await expect(page.getByText(UNOFFICIAL, { exact: true })).toBeVisible(); // empty sheet too
    await tagJourneyByApi(page, matchId);
    await page.reload();
    await expect(page.getByText(UNOFFICIAL, { exact: true })).toBeVisible();
  });

  for (const width of [320, 360, 768, 1280]) {
    test(`Narrow phone screen: score sheet at ${width} px has no sideways scrolling`, async ({ page }, testInfo) => {
      const matchId = await receivedMatch(page);
      await tagJourneyByApi(page, matchId);
      await page.setViewportSize({ width, height: 800 });
      await page.goto(`/matches/${matchId}/sheet`);
      await expect(page.getByRole('table', { name: 'Game 1' })).toBeVisible();
      await expectNoSidewaysScroll(page);
      // Every rally's details are on screen as text with their labels.
      const row = page.getByRole('row', { name: /Rally 6/ });
      await expect(row).toContainText('2-0-1');
      await expect(row).toContainText('Your side');
      if (width <= 360) await expectNoBlockingA11yViolations(page, testInfo, `S-01-${width}`);
    });
  }
});
