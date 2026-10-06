// Binds tests/features/undo_and_audit.feature in the browser (QA-ACC for ST-031; FR-052) and
// E2E-02-06: undo restores the score sheet exactly, and the correction history H-01 lists the
// change and the undo in words. Axe on S-01 and H-01.
import { expect, test } from '@playwright/test';
import { expectNoBlockingA11yViolations, expectTargetsAtLeast24 } from '../helpers/axe';
import { receivedMatch, sheetOf, tagJourneyByApi } from '../helpers/sprint-02';

test.describe('@M0 @story-ST-031 Undo and correction history', () => {
  test('E2E-02-06 undo restores the sheet and the history lists the change and the undo', async ({ page }, testInfo) => {
    const matchId = await receivedMatch(page);
    await tagJourneyByApi(page, matchId);
    const before = await sheetOf(page, matchId);

    await page.goto(`/matches/${matchId}/sheet`);
    const history = page.getByRole('list', { name: 'Correction history' });
    await expect(page.getByText('No changes yet.').or(history)).toBeVisible();
    await expectNoBlockingA11yViolations(page, testInfo, 'S-01');

    // Rally 2 was won by the other side: switch it to Ivy's side (one tap).
    await page.getByRole('button', { name: 'Rally 2: change the winner to your side' }).click();
    await expect(page.getByRole('status').filter({ hasText: 'Rally 2 corrected' })).toBeVisible();
    await expect(history.getByText('Rally 2: won by changed from the other side to your side')).toBeVisible();
    await expect(page.getByRole('row', { name: /Rally 2/ }).getByText('corrected by you')).toBeVisible();
    expect((await sheetOf(page, matchId)).rows[1]?.score_after).toBe('2-0-2'); // rallies 2-6 re-scored
    await expectNoBlockingA11yViolations(page, testInfo, 'H-01');
    await expectTargetsAtLeast24(page, testInfo, 'H-01');

    await page.getByRole('button', { name: 'Undo last change' }).click();
    await expect(page.getByRole('status').filter({ hasText: 'Last change undone.' })).toBeVisible();
    await expect(history.getByText('Undone: Rally 2: won by changed from the other side to your side')).toBeVisible();
    await expect(history.getByRole('listitem').filter({ hasText: /^Rally 2: won by changed/ })).toHaveCount(1);
    await expect(page.getByText('corrected by you')).toHaveCount(0);

    const after = await sheetOf(page, matchId);
    expect(JSON.stringify(after)).toBe(JSON.stringify(before)); // byte-identical (C-04)
  });

  test('Correction history shows what changed', async ({ page }) => {
    const matchId = await receivedMatch(page);
    await tagJourneyByApi(page, matchId);
    await page.goto(`/matches/${matchId}/sheet`);
    await page.getByRole('combobox', { name: 'Rally 6 ending' }).selectOption('forced_error');
    await expect(
      page.getByRole('list', { name: 'Correction history' }).getByText('Rally 6: ending changed from winner to forced error'),
    ).toBeVisible();
  });
});
