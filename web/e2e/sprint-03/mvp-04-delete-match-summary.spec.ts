// MVP-04 browser binding of tests/features/mvp_04_delete_match_summary.feature (ST-050, FR-006;
// flows D-2, X-01). Against the running stack: a match created without a title gets the server's
// default title "Doubles · 5 Sep 2026"; "Delete this match?" names it with the date once. A match
// with a title of the player's own still shows its date. Nothing is deleted here (Cancel).
import { expect, test, type Page } from '@playwright/test';
import { expectNoBlockingA11yViolations } from '../helpers/axe';
import { signInByLink } from '../helpers/sprint-01';
import { SCREEN } from '../helpers/sprint-03';

const PARTICIPANTS = [
  { slot: 'A1', nickname: 'Ivy', is_me: true }, { slot: 'A2', nickname: 'Dana', is_me: false },
  { slot: 'B1', nickname: 'Carlos', is_me: false }, { slot: 'B2', nickname: 'Sam', is_me: false },
];

async function openDeleteDialog(page: Page, body: Record<string, unknown>) {
  const created = await page.request.post('/api/matches', { data: { format: 'doubles', participants: PARTICIPANTS, ...body } });
  expect(created.status()).toBe(201);
  const { id } = (await created.json()) as { id: string };
  await page.goto(`/matches/${id}`);
  await page.getByRole('button', { name: 'Delete match' }).click();
  return page.getByRole('dialog', { name: 'Delete this match?' });
}

test.describe('@M0 @story-ST-050 @ticket-MVP-04 The delete confirmation names the match once', () => {
  test('MVP-04-E2E-01 a match with its default title shows the date once', async ({ page }, testInfo) => {
    await signInByLink(page);
    const dialog = await openDeleteDialog(page, { played_on: '2026-09-05' });
    await expect(dialog.getByText('Doubles · 5 Sep 2026', { exact: true })).toBeVisible();
    const text = (await dialog.textContent()) ?? '';
    expect(text.match(/5 Sept? 2026/g) ?? []).toHaveLength(1);
    await expectNoBlockingA11yViolations(page, testInfo, SCREEN.deleteMatch);
    await dialog.getByRole('button', { name: 'Cancel' }).click();
    await expect(page.getByRole('dialog')).toHaveCount(0);
  });

  test('MVP-04-E2E-02 a match with a title of her own shows the title and the date', async ({ page }) => {
    await signInByLink(page);
    const dialog = await openDeleteDialog(page, { title: 'Saturday doubles', played_on: '2026-10-03' });
    await expect(dialog.getByText('Saturday doubles · 3 Oct 2026', { exact: true })).toBeVisible();
    await dialog.getByRole('button', { name: 'Cancel' }).click();
  });

  test('MVP-04-E2E-03 a title naming a later day ending in the same digit keeps the date played', async ({ page }) => {
    await signInByLink(page);
    const dialog = await openDeleteDialog(page, { title: 'Doubles · 15 Sep 2026', played_on: '2026-09-05' });
    await expect(dialog.getByText('Doubles · 15 Sep 2026 · 5 Sept 2026', { exact: true })).toBeVisible();
    await dialog.getByRole('button', { name: 'Cancel' }).click();
  });
});
