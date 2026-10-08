// E2E-03-07 (C3-03, PE-S2-R3-01; Gherkin §7.7 corrections_replay "Only moves the server accepts
// are offered"). Red first against the Sprint 2 S-01, which offered "Move rally n to the next
// game" on rallies 12 and 13 that the server refuses with decision/not_last_in_game. Same setup
// as IT-02-14 r2: game 1 tagged 10 A, B, A, A, A; correcting rally 11 to A ends game 1 at rally
// 11, so rallies 12-14 need a decision; game 2 is started. Provisional rules, @needs-verification.
import { expect, test } from '@playwright/test';
import { expectNoBlockingA11yViolations } from '../helpers/axe';
import { receivedMatch, sheetOf } from '../helpers/sprint-02';

async function version(page: import('@playwright/test').Page, matchId: string): Promise<number> {
  const r = await page.request.get(`/api/matches/${matchId}/score-sheet`);
  return Number((r.headers()['etag'] ?? '0').replace(/"/g, ''));
}

test.describe('@M0 @story-C3-03 @needs-verification Only moves the server accepts are offered', () => {
  test('E2E-03-07 "Move to the next game" is offered only on the latest kept rally', async ({ page }, testInfo) => {
    const matchId = await receivedMatch(page, 'E2E-03-07 move offer');
    let v = await version(page, matchId);
    const start = await page.request.post(`/api/matches/${matchId}/games`, {
      headers: { 'If-Match': `"${v}"` }, data: { first_serving_side: 'A', ends_switched: false },
    });
    expect(start.status(), await start.text()).toBe(201);
    v = ((await start.json()) as { version: number }).version;
    for (const [i, side] of [...'AAAAAAAAAABAAA'].entries()) {
      const r = await page.request.post(`/api/matches/${matchId}/rallies`, {
        headers: { 'If-Match': `"${v}"` },
        data: { start_ms: i * 4000, end_ms: i * 4000 + 2000, winning_side: side, ending: 'winner', responsible_player: null, fault_kind: null },
      });
      expect(r.status(), await r.text()).toBe(201);
      v = ((await r.json()) as { version: number }).version;
    }
    const ids = (await sheetOf(page, matchId)).rows.map((r) => r.rally_id);
    const fix = await page.request.patch(`/api/matches/${matchId}/rallies/${ids[10]}`, {
      headers: { 'If-Match': `"${v}"` }, data: { field: 'winning_side', value: 'A' },
    });
    expect(fix.status(), await fix.text()).toBe(200);
    v = ((await fix.json()) as { version: number }).version;
    const game2 = await page.request.post(`/api/matches/${matchId}/games`, {
      headers: { 'If-Match': `"${v}"` }, data: { first_serving_side: 'B', ends_switched: false },
    });
    expect(game2.status(), await game2.text()).toBe(201);

    await page.goto(`/matches/${matchId}/sheet`);
    for (const n of [12, 13]) {
      const row = page.getByRole('row', { name: new RegExp(`Rally ${n}\\b`) });
      await expect(row.getByText('needs your decision')).toBeVisible();
      await expect(row.getByRole('button', { name: /to the next game/ })).toHaveCount(0);
      await expect(row).toContainText('Only the last rally of game 1 can move to the next game. Decide rally 14 first.');
    }
    await expectNoBlockingA11yViolations(page, testInfo, 'S-01-move-offer');

    await page.getByRole('button', { name: 'Move rally 14 to the next game' }).click();
    await expect(page.getByRole('status').filter({ hasText: 'Rally 14 moved to the next game.' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Move rally 13 to the next game' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Move rally 12 to the next game' })).toHaveCount(0);
    await expect(page.getByRole('alert').filter({ hasText: /\S/ })).toHaveCount(0); // not Next's empty route announcer
    expect((await sheetOf(page, matchId)).rows.find((r) => r.number === 14)?.marker).toBeNull();
  });
});
