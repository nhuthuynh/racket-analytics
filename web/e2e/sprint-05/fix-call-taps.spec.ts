// ST-080 (NFR-036.4; scorecard G05-05; tests/features/fix_call_taps.feature): every call type in
// docs/domain/fix-call-types.md (COACH-5: CT-1 winner, CT-2 ending, CT-3 fault to and from, CT-4
// player) is fixed in at most 2 taps or keys from the screen where the wrong value is seen, by
// taps and by keys. Each fix is counted by the TapCounter (e2e/helpers/tap-counter.ts), which
// annotates its count as `taps` and fails the test when the count is over 2. Opening the screen
// and reaching the control are not counted, and nor is moving focus (Tab); the count starts on
// the control (fix-call-types.md §2; E2E-02-05, TCR 2026-10-06). The planted 3-step path is a
// real 3-tap detour in the browser, annotated `planted-taps` so it never raises the G05-05 max.
import { expect, test, type Page } from '@playwright/test';
import { JOURNEY, openTagging, receivedMatch, sheetOf, tagByKeys, tagJourneyByApi, type SheetRowShape } from '../helpers/sprint-02';
import { TapCounter } from '../helpers/tap-counter';

/** The JOURNEY match on its score sheet (S-01), where every call is seen. */
async function journeySheet(page: Page): Promise<string> {
  const matchId = await receivedMatch(page);
  await tagJourneyByApi(page, matchId);
  await page.goto(`/matches/${matchId}/sheet`);
  await expect(page.getByRole('table', { name: 'Game 1' })).toBeVisible();
  return matchId;
}

async function rally(page: Page, matchId: string, n: number): Promise<SheetRowShape> {
  return (await sheetOf(page, matchId)).rows[n - 1]!;
}

/** By taps: open a disclosure on rally n, then press its option. */
async function tapOption(counter: TapCounter, page: Page, n: number, toggle: 'Change ending' | 'Change player', option: string) {
  const group = toggle === 'Change ending' ? `Rally ${n} ending` : `Rally ${n} player`;
  await counter.tap(page.getByRole('button', { name: `${toggle}, rally ${n}` }), `${toggle}, rally ${n}`);
  await counter.tap(page.getByRole('group', { name: group }).getByRole('button', { name: option, exact: true }), option);
}

/** By keys: the control has focus (not counted), Enter opens, Tab moves to the option, Enter saves. */
async function keyOption(counter: TapCounter, page: Page, n: number, toggle: 'Change ending' | 'Change player', option: string) {
  const group = toggle === 'Change ending' ? `Rally ${n} ending` : `Rally ${n} player`;
  await page.getByRole('button', { name: `${toggle}, rally ${n}` }).focus();
  await counter.key('Enter', `open ${toggle}, rally ${n}`);
  const target = page.getByRole('group', { name: group }).getByRole('button', { name: option, exact: true });
  for (let moves = 0; moves < 8 && !(await target.evaluate((el) => el === document.activeElement)); moves += 1) {
    await counter.move('Tab');
  }
  await expect(target).toBeFocused();
  await counter.key('Enter', option);
}

function done(counter: TapCounter, label: string): void {
  counter.report(test.info(), label);
  counter.expectWithinBudget();
}

test.describe('@M5 @story-ST-080 Fixing a call is quick (NFR-036.4)', () => {
  test('E2E-05-80 a call is fixed in at most 2 taps or keys from where it is seen: CT-1 rally winner', async ({ page }) => {
    const matchId = await journeySheet(page);
    expect(await rally(page, matchId, 2)).toMatchObject({ winning_side: 'B', ending: 'unforced_error' });
    const taps = new TapCounter(page);
    await taps.tap(page.getByRole('button', { name: /^Switch winner, rally 2, to / }), 'Switch winner, rally 2');
    await expect.poll(async () => (await rally(page, matchId, 2)).winning_side).toBe('A');
    done(taps, 'CT-1 by taps: rally 2 won by B to won by A');

    expect((await rally(page, matchId, 6)).winning_side).toBe('A');
    const keys = new TapCounter(page);
    await page.getByRole('button', { name: /^Switch winner, rally 6, to / }).focus();
    await keys.key('Enter', 'Switch winner, rally 6');
    await expect.poll(async () => (await rally(page, matchId, 6)).winning_side).toBe('B');
    done(keys, 'CT-1 by keys: rally 6 won by A to won by B');
  });

  test('E2E-05-80 a call is fixed in at most 2 taps or keys from where it is seen: CT-2 rally ending', async ({ page }) => {
    const matchId = await journeySheet(page);
    expect((await rally(page, matchId, 6)).ending).toBe('winner');
    const taps = new TapCounter(page);
    await tapOption(taps, page, 6, 'Change ending', 'Unforced error');
    await expect.poll(async () => (await rally(page, matchId, 6)).ending).toBe('unforced_error');
    done(taps, 'CT-2 by taps: rally 6 winner to unforced error');

    expect((await rally(page, matchId, 2)).ending).toBe('unforced_error');
    const keys = new TapCounter(page);
    await keyOption(keys, page, 2, 'Change ending', 'Replay');
    await expect.poll(async () => (await rally(page, matchId, 2)).ending).toBe('replay');
    expect((await rally(page, matchId, 2)).winning_side, 'a replay has no winner').toBeNull();
    done(keys, 'CT-2 by keys: rally 2 unforced error to replay');
  });

  test('E2E-05-80 a call is fixed in at most 2 taps or keys from where it is seen: CT-3 fault', async ({ page }) => {
    const matchId = await journeySheet(page);
    expect((await rally(page, matchId, 2)).ending).toBe('unforced_error');
    const taps = new TapCounter(page);
    await tapOption(taps, page, 2, 'Change ending', 'Fault');
    await expect.poll(async () => (await rally(page, matchId, 2)).ending).toBe('fault');
    done(taps, 'CT-3 by taps: rally 2 unforced error to fault');

    expect((await rally(page, matchId, 4)).ending).toBe('fault');
    const keys = new TapCounter(page);
    await keyOption(keys, page, 4, 'Change ending', 'Forced error');
    await expect.poll(async () => (await rally(page, matchId, 4)).ending).toBe('forced_error');
    done(keys, 'CT-3 by keys: rally 4 fault to forced error');
  });

  test('E2E-05-80 a call is fixed in at most 2 taps or keys from where it is seen: CT-4 responsible player', async ({ page }) => {
    const matchId = await journeySheet(page);
    // Setup, not counted: rally 2 (an unforced error by side A) is tagged on Ivy.
    await page.getByRole('button', { name: 'Change player, rally 2' }).click();
    await page.getByRole('group', { name: 'Rally 2 player' }).getByRole('button', { name: 'Ivy', exact: true }).click();
    await expect.poll(async () => (await rally(page, matchId, 2)).responsible_player).toBe('A1');

    const taps = new TapCounter(page);
    await tapOption(taps, page, 2, 'Change player', 'Dana');
    await expect.poll(async () => (await rally(page, matchId, 2)).responsible_player).toBe('A2');
    done(taps, 'CT-4 by taps: rally 2 Ivy to her partner Dana');

    const keys = new TapCounter(page);
    await keyOption(keys, page, 2, 'Change player', 'Not tagged');
    await expect.poll(async () => (await rally(page, matchId, 2)).responsible_player).toBeNull();
    expect((await rally(page, matchId, 2)).ending, 'the ending is kept').toBe('unforced_error');
    done(keys, 'CT-4 by keys: rally 2 Dana to not tagged');
  });

  test('E2E-05-80 the wrong last tag is removed from Quick Tag in 1 key', async ({ page }) => {
    const matchId = await receivedMatch(page);
    await openTagging(page, matchId);
    await tagByKeys(page, JOURNEY[0]!, 1);
    await tagByKeys(page, { side: 'other', ending: 'winner' }, 2); // the wrong call, seen as the last tag
    const keys = new TapCounter(page);
    await keys.key('z', 'undo the last tag');
    await expect(page.getByRole('status').filter({ hasText: 'Last change undone.' })).toBeVisible();
    await expect.poll(async () => (await sheetOf(page, matchId)).rows.length).toBe(1);
    done(keys, 'Quick Tag by keys: the wrong last tag undone');
  });

  test('E2E-05-80 a planted 3-step path is counted as 3 and fails the budget', async ({ page }) => {
    const matchId = await journeySheet(page);
    const detour = new TapCounter(page);
    // CT-3 by a detour (fix-call-types.md §4): the wrong disclosure first, then the right one.
    await detour.tap(page.getByRole('button', { name: 'Change player, rally 2' }), 'Change player, rally 2');
    await tapOption(detour, page, 2, 'Change ending', 'Fault');
    await expect.poll(async () => (await rally(page, matchId, 2)).ending).toBe('fault');
    detour.report(test.info(), 'planted CT-3 detour: rally 2 unforced error to fault', 'planted-taps');
    expect(detour.count).toBe(3);
    expect(detour.problem()).toBe('3 taps or keys, over the budget of 2');
    expect(() => detour.expectWithinBudget()).toThrow(/over the budget of 2/);
  });
});
