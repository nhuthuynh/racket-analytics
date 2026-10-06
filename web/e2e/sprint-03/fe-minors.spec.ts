// Sprint 2 review round 3 FE minors carried to Sprint 3 (C3-10), live on the stack:
// PD-R3S2-01 T-02 errors use the shared error summary [DPA/DESIGN-13];
// PD-R3S2-02 H-01 says when "Reload the history" failed again.
import { expect, test } from '@playwright/test';
import { expectNoBlockingA11yViolations } from '../helpers/axe';
import { MY_SIDE, receivedMatch } from '../helpers/sprint-02';

test.describe('@story-C3-10 FE minors from Sprint 2 review round 3', () => {
  test('PD-R3S2-01 T-02 with no choice shows the error summary, which links to the question', async ({ page }, testInfo) => {
    const matchId = await receivedMatch(page, 'PD-R3S2-01 T-02');
    await page.goto(`/matches/${matchId}/tag`);
    await page.getByRole('button', { name: 'Start game 1' }).click();
    const summary = page.getByRole('alert').filter({ hasText: 'There is a problem' });
    await expect(summary).toBeFocused();
    await expect(page.getByRole('group', { name: 'Who serves first in game 1?' })).toContainText('Choose who serves first in game 1.');
    await expectNoBlockingA11yViolations(page, testInfo, 'T-02-error');
    await summary.getByRole('link', { name: 'Choose who serves first in game 1.' }).click();
    await expect(page.getByRole('radio', { name: MY_SIDE })).toBeFocused();
    await page.keyboard.press('Space');
    await page.getByRole('button', { name: 'Start game 1' }).click();
    await expect(page.getByRole('group', { name: 'Tag the rally' })).toBeVisible();
  });
});
