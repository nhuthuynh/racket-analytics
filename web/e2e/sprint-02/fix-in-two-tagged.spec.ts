// E2E-02-05 continued (QA-ACC for ST-032; NFR-036 (d) "any call is fixed in at most 2 taps or
// keys"; FR-052, FR-053). PD-S2R1-07: fix-in-two.spec.ts proves (d) only on a rally with no
// tagged player, and counted one arrow key that saved on change as the fix. These cases close
// that gap:
//   - "Switch winner" on every rally with a tagged player (JOURNEY rallies 1, 3, 4: a winner, a
//     forced error, a fault) is 1 tap, really changes the winner, and writes 1 history line
//     (PD-S2R1-01);
//   - an ending changed with keys from "Winner" to "Fault" is 2 keys (Enter opens, Enter on the
//     option saves; Tab is moving, not fixing) and writes exactly 1 history line: moving over
//     "Unforced error" and "Forced error" on the way saves nothing (PD-S2R1-02, WCAG SC 3.2.2).
// Counted: the activations after the control is reached, as in fix-in-two.spec.ts.
import { expect, test, type Page } from '@playwright/test';
import { JOURNEY, receivedMatch, sheetOf, tagJourneyByApi } from '../helpers/sprint-02';

async function historyCount(page: Page, matchId: string): Promise<number> {
  const r = await page.request.get(`/api/matches/${matchId}/corrections`);
  expect(r.status(), await r.text()).toBe(200);
  return ((await r.json()) as { items: unknown[] }).items.length;
}

async function journeySheet(page: Page): Promise<string> {
  const matchId = await receivedMatch(page);
  await tagJourneyByApi(page, matchId);
  await page.goto(`/matches/${matchId}/sheet`);
  await expect(page.getByRole('table', { name: 'Game 1' })).toBeVisible();
  return matchId;
}

test.describe('@M0 @story-ST-032 Fix a call quickly, rallies with a tagged player (PD-S2R1-07)', () => {
  test('E2E-02-05 the winner of a rally with a tagged player is fixed in 1 tap, 1 history line', async ({ page }) => {
    const matchId = await journeySheet(page);
    const tagged = JOURNEY.flatMap((tag, i) => (tag.player ? [i + 1] : []));
    expect(tagged, 'JOURNEY rallies with a tagged player').toEqual([1, 3, 4]);

    for (const n of tagged) {
      const before = (await sheetOf(page, matchId)).rows[n - 1]!;
      const lines = await historyCount(page, matchId);
      let actions = 0;
      await page.getByRole('button', { name: new RegExp(`^Rally ${n}: change the winner to `) }).click();
      actions += 1;
      await expect(page.getByRole('status').filter({ hasText: `Rally ${n} corrected` })).toBeVisible();
      await expect(page.getByRole('alert').filter({ hasText: /\S/ })).toHaveCount(0);
      expect(actions).toBeLessThanOrEqual(2);
      const after = (await sheetOf(page, matchId)).rows[n - 1]!;
      expect(after.winning_side, `rally ${n} winner`).not.toBe(before.winning_side);
      expect(after.winning_side, `rally ${n} winner`).not.toBeNull();
      expect(after.ending, `rally ${n} ending is kept`).toBe(before.ending);
      expect(await historyCount(page, matchId), `rally ${n}: one tap, one history line`).toBe(lines + 1);
    }
  });

  test('E2E-02-05 an ending is changed with keys from winner to fault in 2 keys, 1 history line', async ({ page }) => {
    const matchId = await journeySheet(page);
    expect((await sheetOf(page, matchId)).rows[0]?.ending).toBe('winner');
    const lines = await historyCount(page, matchId);
    let actions = 0;

    await page.getByRole('button', { name: 'Change ending, rally 1' }).focus();
    await page.keyboard.press('Enter');
    actions += 1;
    const fault = page.getByRole('group', { name: 'Rally 1 ending' }).getByRole('button', { name: 'Fault', exact: true });
    // Moving (not counted): Tab over the options until "Fault" has focus, passing "Unforced
    // error" and "Forced error". A list that saved on change would write a line for each.
    for (let moves = 0; moves < 8 && !(await fault.evaluate((el) => el === document.activeElement)); moves += 1) {
      await page.keyboard.press('Tab');
    }
    await expect(fault).toBeFocused();
    expect(await historyCount(page, matchId), 'moving over the options saves nothing').toBe(lines);
    await page.keyboard.press('Enter');
    actions += 1;

    await expect(page.getByRole('status').filter({ hasText: 'Rally 1 corrected' })).toBeVisible();
    expect(actions).toBeLessThanOrEqual(2);
    await expect.poll(async () => (await sheetOf(page, matchId)).rows[0]?.ending).toBe('fault');
    expect(await historyCount(page, matchId), 'one fix, one history line').toBe(lines + 1);
  });
});
