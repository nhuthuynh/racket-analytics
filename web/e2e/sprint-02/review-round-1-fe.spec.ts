// Review round 1 (Sprint 2), senior-frontend-engineer fixes, checked in a real browser on the live
// stack: PD-S2R1-01 (Switch winner works on a rally with a tagged player), PD-S2R1-02 (moving
// through the correction options saves nothing), PD-S2R1-04 (K-01 returns focus to its opener),
// PD-S2R1-05 (a failed rally video returns focus to "Watch rally n"), PD-S2R1-06 (no call or
// server before game 1 starts), PD-R2R-03 (G-01 consent line). Negative cases first.
import { expect, test, type Page } from '@playwright/test';
import { signInByLink } from '../helpers/sprint-01';
import { MY_SIDE, openTagging, receivedMatch, sheetOf, tagJourneyByApi } from '../helpers/sprint-02';

test.use({ serviceWorkers: 'block' }); // PD-S2R1-05 routes the media request (TCR 2026-10-05)

async function historyCount(page: Page, matchId: string): Promise<number> {
  const r = await page.request.get(`/api/matches/${matchId}/corrections`);
  expect(r.status(), await r.text()).toBe(200);
  return ((await r.json()) as { items: unknown[] }).items.length;
}

const focusedTag = (page: Page) =>
  page.evaluate(() => {
    const el = document.activeElement;
    return el ? `${el.tagName}:${(el.getAttribute('aria-label') ?? el.textContent ?? '').trim().slice(0, 40)}` : 'none';
  });

test.describe('@M0 @story-ST-032 Score sheet corrections (review round 1)', () => {
  test('PD-S2R1-02 arrow keys in the ending and player options save nothing', async ({ page }) => {
    const matchId = await receivedMatch(page);
    await tagJourneyByApi(page, matchId);
    await page.goto(`/matches/${matchId}/sheet`);
    const before = await historyCount(page, matchId);
    await expect(page.getByRole('combobox')).toHaveCount(0);
    await page.getByRole('button', { name: 'Change ending, rally 2' }).focus();
    await page.keyboard.press('Enter');
    for (const key of ['Tab', 'ArrowDown', 'ArrowDown', 'ArrowDown', 'ArrowUp']) await page.keyboard.press(key);
    await page.keyboard.press('Escape');
    await expect(page.getByRole('button', { name: 'Change ending, rally 2' })).toBeFocused();
    await page.getByRole('button', { name: 'Change player, rally 2' }).focus();
    await page.keyboard.press('Enter');
    for (const key of ['Tab', 'ArrowDown', 'ArrowDown']) await page.keyboard.press(key);
    await page.waitForTimeout(1500); // a saved correction would have landed by now
    expect(await historyCount(page, matchId)).toBe(before);
    expect((await sheetOf(page, matchId)).rows[1]?.ending).toBe('unforced_error');
  });

  test('PD-S2R1-01 Switch winner fixes a rally with a tagged player in 1 tap', async ({ page }) => {
    const matchId = await receivedMatch(page);
    await tagJourneyByApi(page, matchId);
    await page.goto(`/matches/${matchId}/sheet`);
    // Rally 1 winner (Ivy), rally 3 forced error (Carlos), rally 4 fault (Sam).
    for (const n of [1, 3, 4]) {
      const before = (await sheetOf(page, matchId)).rows[n - 1]!;
      await page.getByRole('button', { name: new RegExp(`^Switch winner, rally ${n},`) }).click();
      await expect(page.getByRole('status').filter({ hasText: `Rally ${n} corrected` })).toBeVisible();
      await expect(page.locator('.notice--error')).toHaveCount(0);
      const after = (await sheetOf(page, matchId)).rows[n - 1]!;
      expect(after.winning_side).not.toBe(before.winning_side);
      expect(after.ending).toBe(before.ending);
      expect((after as { responsible_player?: string | null }).responsible_player ?? null).toBeNull();
    }
    await expect(page.getByRole('list', { name: 'Correction history' })).toContainText(
      'Rally 1: won by changed from your side to the other side, player changed from Ivy to not tagged',
    );
  });

  test('PD-S2R1-05 a failed rally video returns focus to "Watch rally n"', async ({ page }) => {
    const matchId = await receivedMatch(page);
    await tagJourneyByApi(page, matchId);
    await page.route('**/racket-media/**', (route) => route.fulfill({ status: 403, body: 'denied' }));
    await page.goto(`/matches/${matchId}/sheet`);
    await page.getByRole('button', { name: 'Watch rally 3' }).click();
    await expect(page.getByRole('alert').filter({ hasText: "This video link no longer works. Choose 'Watch rally 3' again." })).toBeVisible();
    await expect(page.locator('video')).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Watch rally 3' })).toBeFocused();
  });
});

test.describe('@M0 @story-ST-027 @story-ST-028 Tagging screen (review round 1)', () => {
  test('PD-S2R1-06 before game 1 starts there is no call and no server line', async ({ page }) => {
    const matchId = await receivedMatch(page);
    await page.goto(`/matches/${matchId}/tag`);
    await expect(page.getByText('Who serves first in game 1?')).toBeVisible();
    const score = page.getByRole('group', { name: 'Score' });
    await expect(score).not.toContainText('0-0-2');
    await expect(score).not.toContainText('serves');
    await page.getByRole('radio', { name: MY_SIDE }).check();
    await page.getByRole('button', { name: 'Start game 1' }).click();
    await expect(score).toContainText('0-0-2');
    await expect(score).toContainText('Your side serves');
  });

  test('PD-S2R1-04 K-01 returns focus to the control that opened it', async ({ page }) => {
    await openTagging(page, await receivedMatch(page));
    const opener = page.getByRole('button', { name: 'Keyboard shortcuts' });
    const dialog = page.getByRole('dialog', { name: 'Keyboard shortcuts' });

    await opener.click();
    await expect(dialog).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(dialog).toHaveCount(0);
    await expect(opener, `after Esc: ${await focusedTag(page)}`).toBeFocused();

    await opener.click();
    await dialog.getByRole('button', { name: 'Close' }).click();
    await expect(dialog).toHaveCount(0);
    await expect(opener, `after Close: ${await focusedTag(page)}`).toBeFocused();

    const start = page.getByRole('button', { name: 'Rally start' });
    await start.focus();
    await page.keyboard.press('?');
    await expect(dialog).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(start, `after ? then Esc: ${await focusedTag(page)}`).toBeFocused();
  });
});

test.describe('@M0 @story-ST-015 Capture guide (review round 1)', () => {
  test('PD-R2R-03 G-01 shows the consent courtesy line', async ({ page }) => {
    await signInByLink(page);
    await page.goto('/guide');
    const line = page.getByText("Film only people who agree to be filmed. Don't upload matches with anyone under 18.", { exact: true });
    await expect(line).toBeVisible();
    await expect(line).toHaveClass(/notice/);
  });
});
