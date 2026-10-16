// MVP-02 (MVP goal; FR-050), live on the stack. Binds tests/features/tag_without_video.feature.
// The live finding (main 6c666b9, headless Chromium without H.264): T-01 said the browser cannot
// play the video and offered tagging without it, but only rally 1 was saved. Every browser here
// is given the same unplayable video: the media request is aborted, and the <video> reports what
// the live run saw (metadata, readyState 1; a decode error; its time stuck at 0).
import { expect, test, type Page } from '@playwright/test';
import { MY_SIDE, OTHER_SIDE, openTagging, receivedMatch, sheetOf } from '../helpers/sprint-02';

test.use({ serviceWorkers: 'block' }); // the media request is routed (route isolation guard)

async function unplayableVideo(page: Page): Promise<void> {
  await page.route(/X-Amz-Signature=/, (route) => route.abort());
  await page.addInitScript(() => {
    const proto = HTMLMediaElement.prototype;
    Object.defineProperty(proto, 'readyState', { configurable: true, get: () => 1 });
    Object.defineProperty(proto, 'currentTime', { configurable: true, get: () => 0, set: () => {} });
    Object.defineProperty(proto, 'error', { configurable: true, get: () => ({ code: 3, message: 'MVP-02 decode error' }) });
    proto.canPlayType = () => '';
  });
}

/** Tag one rally by taps, the page clock moving on between the marks (no video time). */
async function tagWithoutVideo(page: Page, number: number, side: 'mine' | 'other'): Promise<void> {
  const bar = page.getByRole('group', { name: 'Tag the rally' });
  await bar.getByRole('button', { name: 'Rally start' }).click();
  await expect(page.getByText(/This rally starts before the end of rally/)).toHaveCount(0);
  await expect(bar.getByRole('button', { name: 'Rally start' })).toHaveAttribute('aria-pressed', 'true');
  await page.waitForFunction((t0) => performance.now() - t0 > 50, await page.evaluate(() => performance.now()));
  await bar.getByRole('button', { name: 'Rally end' }).click();
  await bar.getByRole('button', { name: side === 'mine' ? MY_SIDE : OTHER_SIDE }).click();
  await bar.getByRole('button', { name: 'Winner', exact: true }).click();
  await expect(page.getByRole('status').filter({ hasText: new RegExp(`^Rally ${number}:`) }).first()).toBeVisible();
}

test.describe('@story-MVP-02 Tagging without a playable video', () => {
  test('a later rally start is not refused, and three rallies make three score sheet rows', async ({ page }) => {
    const matchId = await receivedMatch(page, 'MVP-02 no video');
    await unplayableVideo(page);
    await openTagging(page, matchId);
    await expect(page.getByText('This browser cannot play this video.', { exact: false })).toBeVisible();
    await expect(page.getByText('If you tag without it, the rally times will not match the video.', { exact: false })).toBeVisible();

    await tagWithoutVideo(page, 1, 'mine');
    await tagWithoutVideo(page, 2, 'other');
    await tagWithoutVideo(page, 3, 'mine');

    const rows = (await sheetOf(page, matchId)).rows as unknown as { number: number; start_ms: number; end_ms: number }[];
    expect(rows.map((r) => r.number)).toEqual([1, 2, 3]);
    for (const [i, r] of rows.entries()) {
      expect(r.end_ms).toBeGreaterThan(r.start_ms);
      if (i > 0) expect(r.start_ms).toBeGreaterThanOrEqual(rows[i - 1]!.end_ms);
    }

    await page.goto(`/matches/${matchId}/sheet`);
    const table = page.getByRole('table', { name: 'Game 1' });
    await expect(table.getByRole('row', { name: /^Rally \d/ })).toHaveCount(3);
  });
});
