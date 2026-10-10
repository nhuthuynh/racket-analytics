// Sprint 2 review round 3 FE minors carried to Sprint 3 (C3-10), live on the stack:
// PD-R3S2-01 T-02 errors use the shared error summary [DPA/DESIGN-13];
// PD-R3S2-02 H-01 says when "Reload the history" failed again and that it is reloading.
// Binds tests/features/game_start_errors.feature and tests/features/history_reload.feature.
import { expect, test } from '@playwright/test';
import { expectNoBlockingA11yViolations } from '../helpers/axe';
import { MY_SIDE, receivedMatch, tagJourneyByApi } from '../helpers/sprint-02';

test.use({ serviceWorkers: 'block' }); // PD-R3S2-02 routes the corrections request (TCR 2026-10-08)

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

  test('PD-R3S2-02 a failed history reload says so; a working one shows the history', async ({ page }, testInfo) => {
    const matchId = await receivedMatch(page, 'PD-R3S2-02 H-01');
    await tagJourneyByApi(page, matchId);
    let failing = true;
    await page.route(`**/api/matches/${matchId}/corrections**`, (route) =>
      failing ? route.fulfill({ status: 503, contentType: 'application/json', body: '{"error":{"code":"unknown"}}' }) : route.continue(),
    );
    await page.goto(`/matches/${matchId}/sheet`);
    const history = page.getByRole('region', { name: 'Correction history' });
    await expect(history).toContainText('The correction history could not be loaded.');
    await history.getByRole('button', { name: 'Reload the history' }).click();
    await expect(history.getByRole('alert')).toHaveText(
      'The history still could not be loaded (tried 2 times). Check your connection, then reload it again.',
    );
    await expectNoBlockingA11yViolations(page, testInfo, 'H-01-reload-failed');
    failing = false;
    await history.getByRole('button', { name: 'Reload the history' }).click();
    await expect(history.getByRole('alert')).toHaveCount(0);
    await expect(history.getByRole('button', { name: /Reload the history/ })).toHaveCount(0);
  });

  test('PD-R3S2-02 while the history reloads the button says so and is busy', async ({ page }) => {
    const matchId = await receivedMatch(page, 'PD-R3S2-02 H-01 busy');
    await tagJourneyByApi(page, matchId);
    let mode: 'fail' | 'hold' = 'fail';
    let release: () => void = () => {};
    const held = new Promise<void>((r) => {
      release = r;
    });
    await page.route(`**/api/matches/${matchId}/corrections**`, async (route) => {
      if (mode === 'fail') return route.fulfill({ status: 503, contentType: 'application/json', body: '{"error":{"code":"unknown"}}' });
      await held;
      return route.continue();
    });
    await page.goto(`/matches/${matchId}/sheet`);
    const history = page.getByRole('region', { name: 'Correction history' });
    await expect(history).toContainText('The correction history could not be loaded.');
    mode = 'hold';
    await history.getByRole('button', { name: 'Reload the history' }).click();
    const busy = history.getByRole('button', { name: 'Reloading the history…' });
    await expect(busy).toHaveAttribute('aria-busy', 'true');
    release();
    await expect(history.getByRole('button', { name: /Reload/ })).toHaveCount(0);
    await expect(history.getByRole('alert')).toHaveCount(0);
  });
});
