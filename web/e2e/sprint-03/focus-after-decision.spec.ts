// DR-02 R2-5 / flows-sprint-02 §12 E-3 (FE follow-up): after a decision removes the row's
// controls, focus goes to the next row's first action, else to "Undo last change"; it never
// drops to the page (SC 2.4.3). Keyboard only, on the live stack. Setup as E2E-03-07: rallies
// 12-14 need a decision after rally 11 is corrected; game 2 is started. @needs-verification.
import { expect, test, type Page } from '@playwright/test';
import { receivedMatch } from '../helpers/sprint-02';

async function conflictMatch(page: Page): Promise<string> {
  const matchId = await receivedMatch(page, 'E-3 focus after a decision');
  const etag = async () => Number(((await page.request.get(`/api/matches/${matchId}/score-sheet`)).headers()['etag'] ?? '0').replace(/"/g, ''));
  const post = async (path: string, data: unknown) => {
    const r = await page.request.post(`/api/matches/${matchId}${path}`, { headers: { 'If-Match': `"${await etag()}"` }, data });
    expect(r.status(), await r.text()).toBe(201);
  };
  await post('/games', { first_serving_side: 'A', ends_switched: false });
  for (const [i, side] of [...'AAAAAAAAAABAAA'].entries()) {
    await post('/rallies', { start_ms: i * 4000, end_ms: i * 4000 + 2000, winning_side: side, ending: 'winner', responsible_player: null, fault_kind: null });
  }
  const sheet = (await (await page.request.get(`/api/matches/${matchId}/score-sheet`)).json()) as { rows: { rally_id: string }[] };
  const fix = await page.request.patch(`/api/matches/${matchId}/rallies/${sheet.rows[10]!.rally_id}`, {
    headers: { 'If-Match': `"${await etag()}"` }, data: { field: 'winning_side', value: 'A' },
  });
  expect(fix.status(), await fix.text()).toBe(200);
  await post('/games', { first_serving_side: 'B', ends_switched: false });
  return matchId;
}

test.describe('@story-DR-02 @needs-verification Focus after a decision (E-3)', () => {
  test('removing a rally by keys puts focus on the next row; moving the last puts it on Undo', async ({ page }) => {
    const matchId = await conflictMatch(page);
    await page.goto(`/matches/${matchId}/sheet`);
    await page.getByRole('button', { name: 'Remove rally 12' }).focus();
    await page.keyboard.press('Enter');
    await expect(page.getByRole('status').filter({ hasText: 'Rally 12 removed.' })).toBeVisible();
    // The server renumbers kept rallies: the old rally 13 is now "Rally 12", the old 14 "Rally 13".
    await expect(page.getByRole('button', { name: 'Remove rally 12' })).toBeFocused();

    await page.getByRole('button', { name: 'Move rally 13 to the next game' }).focus();
    await page.keyboard.press('Enter');
    await expect(page.getByRole('status').filter({ hasText: 'Rally 13 moved to the next game.' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Undo last change' })).toBeFocused();
  });
});
