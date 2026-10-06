// E2E-02-05 (QA-ACC for ST-032; NFR-036 (d)): any call can be fixed in at most 2 taps or keys
// from where it is seen. Counted: the activations after the control is reached (Tab is moving,
// not fixing). On S-01: the winner is 1 tap; the ending and the player are 2 (open "Change
// ending" / "Change player", press the option); with keys, Enter opens and Enter on the option
// saves (PD-S2R1-02: nothing saves while moving, TCR 2026-10-06). On T-01 the last tag is undone
// with 1 key.
import { expect, test } from '@playwright/test';
import { JOURNEY, openTagging, receivedMatch, sheetOf, tagByKeys, tagJourneyByApi } from '../helpers/sprint-02';

test.describe('@M0 @story-ST-032 Fix a call quickly', () => {
  test('E2E-02-05 any call is fixed in at most 2 taps or keys', async ({ page }) => {
    const matchId = await receivedMatch(page);
    await tagJourneyByApi(page, matchId);
    await page.goto(`/matches/${matchId}/sheet`);
    let actions = 0;

    // Winner of rally 6 (a winner with no player): 1 tap.
    await page.getByRole('button', { name: 'Rally 6: change the winner to the other side' }).click();
    actions += 1;
    await expect(page.getByRole('status').filter({ hasText: 'Rally 6 corrected' })).toBeVisible();
    expect(actions).toBeLessThanOrEqual(2);
    expect((await sheetOf(page, matchId)).rows[5]?.winning_side).toBe('B');

    // Ending of rally 2: 2 taps (open "Change ending", press the ending).
    actions = 0;
    await page.getByRole('button', { name: 'Change ending, rally 2' }).click();
    actions += 1;
    await page.getByRole('group', { name: 'Rally 2 ending' }).getByRole('button', { name: 'Fault' }).click();
    actions += 1;
    await expect(page.getByRole('status').filter({ hasText: 'Rally 2 corrected' })).toBeVisible();
    expect(actions).toBeLessThanOrEqual(2);
    expect((await sheetOf(page, matchId)).rows[1]?.ending).toBe('fault');

    // Player of rally 2 with keys (the fault was Ivy's): "Change player" has focus, Enter opens,
    // Tab moves to Ivy (the first player who fits), Enter saves: 2 keys.
    actions = 0;
    await page.getByRole('button', { name: 'Change player, rally 2' }).focus();
    await page.keyboard.press('Enter');
    actions += 1;
    await page.keyboard.press('Tab');
    await expect(page.getByRole('group', { name: 'Rally 2 player' }).getByRole('button', { name: 'Ivy' })).toBeFocused();
    await page.keyboard.press('Enter');
    actions += 1;
    await expect.poll(async () => (await sheetOf(page, matchId)).rows[1]?.responsible_player).toBe('A1');
    expect(actions).toBeLessThanOrEqual(2);
  });

  test('E2E-02-05 a wrong last tag is undone with 1 key on the tagging screen', async ({ page }) => {
    const matchId = await receivedMatch(page);
    await openTagging(page, matchId);
    await tagByKeys(page, JOURNEY[0]!, 1);
    await tagByKeys(page, { side: 'other', ending: 'winner' }, 2); // the wrong call
    await page.keyboard.press('z');
    await expect(page.getByRole('status').filter({ hasText: 'Last change undone.' })).toBeVisible();
    expect((await sheetOf(page, matchId)).rows).toHaveLength(1);
  });
});
