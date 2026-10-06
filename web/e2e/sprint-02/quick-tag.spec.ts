// Binds tests/features/quick_tag.feature in the browser (QA-ACC for ST-027; FR-050, NFR-012,
// NFR-028, NFR-060): the on-screen copy of each scenario and the video moment after a tag.
import { expect, test } from '@playwright/test';
import {
  JOURNEY,
  OTHER_SIDE,
  moveRallyClockOn,
  openTagging,
  playableVideo,
  receivedMatch,
  sheetOf,
  tagByTaps,
} from '../helpers/sprint-02';
import { signInByLink } from '../helpers/sprint-01';

test.describe('@M0 @story-ST-027 Quick Tag', () => {
  test('Tag a rally: the score is shown at once and the video continues from the end of the rally', async ({ page }) => {
    await playableVideo(page); // rally times come from the video, as in WebKit (SRE-S2-07)
    const matchId = await receivedMatch(page);
    await openTagging(page, matchId);
    for (const [i, tag] of JOURNEY.entries()) await tagByTaps(page, tag, i + 1);

    // Rally 7: won by the other side, unforced error by Ivy herself.
    const bar = page.getByRole('group', { name: 'Tag the rally' });
    await bar.getByRole('button', { name: 'Rally start' }).click();
    await moveRallyClockOn(page); // SRE-S2-07: a paused video does not move on by itself
    await bar.getByRole('button', { name: 'Rally end' }).click();
    const endMarked = await page.evaluate(() => document.querySelector('video')?.currentTime ?? null);
    await bar.getByRole('button', { name: OTHER_SIDE }).click();
    await bar.getByRole('button', { name: 'Ivy', exact: true }).click();
    await bar.getByRole('button', { name: 'Unforced error', exact: true }).click();
    await expect(page.getByRole('status').filter({ hasText: 'Rally 7: them. Score 2-0-2.' })).toBeVisible();
    await expect(page.locator('.quick-tag__call')).toHaveText('2-0-2');

    const row = (await sheetOf(page, matchId)).rows[6]!;
    expect(row.responsible_player).toBe('A1'); // the error is attributed to her
    // FR-050: the video was not sent back to the start of the rally; ready to mark rally 8.
    if (endMarked !== null) {
      const now = await page.evaluate(() => document.querySelector('video')?.currentTime ?? 0);
      expect(now).toBeGreaterThanOrEqual(endMarked);
    }
    await expect(bar.getByRole('button', { name: 'Rally start' })).toHaveAttribute('aria-pressed', 'false');
  });

  test('Error attributed to the winning side is refused with the reason', async ({ page }) => {
    await playableVideo(page);
    await openTagging(page, await receivedMatch(page));
    const bar = page.getByRole('group', { name: 'Tag the rally' });
    await bar.getByRole('button', { name: 'Rally start' }).click();
    await moveRallyClockOn(page); // SRE-S2-07: a paused video does not move on by itself
    await bar.getByRole('button', { name: 'Rally end' }).click();
    await bar.getByRole('button', { name: /^Your side/ }).click();
    await bar.getByRole('button', { name: 'Dana', exact: true }).click();
    await bar.getByRole('button', { name: 'Unforced error', exact: true }).click();
    await expect(page.getByRole('alert').filter({ hasText: /\S/ })).toContainText(
      'The player who made the error must be on the side',
    );
    expect((await sheetOf(page, page.url().split('/')[4]!)).rows).toEqual([]);
  });

  test('14.3.5 Tag before the video is received', async ({ page }) => {
    await signInByLink(page);
    const created = await page.request.post('/api/matches', { data: { title: 'No video yet', format: 'doubles' } });
    const matchId = ((await created.json()) as { id: string }).id;
    await page.goto(`/matches/${matchId}/tag`);
    await expect(page.getByText('You can tag this match once its video is received.')).toBeVisible();
    await expect(page.getByRole('group', { name: 'Tag the rally' })).toHaveCount(0);
  });

  test('Two devices tag at once: the other device is told and shows the latest score', async ({ browser }) => {
    const phone = await browser.newPage();
    await playableVideo(phone);
    const matchId = await receivedMatch(phone);
    await openTagging(phone, matchId);
    const laptop = await browser.newPage({ storageState: await phone.context().storageState() });
    await playableVideo(laptop);
    await openTagging(laptop, matchId);
    await tagByTaps(phone, JOURNEY[0]!, 1); // the phone saves rally 1 first
    const bar = laptop.getByRole('group', { name: 'Tag the rally' });
    await bar.getByRole('button', { name: 'Rally start' }).click();
    await moveRallyClockOn(laptop);
    await bar.getByRole('button', { name: 'Rally end' }).click();
    await bar.getByRole('button', { name: OTHER_SIDE }).click();
    await bar.getByRole('button', { name: 'Winner', exact: true }).click();
    // The stale tag is not saved; the laptop now shows the phone's rally 1.
    await expect(laptop.getByRole('status').filter({ hasText: /^Rally 1: us/ })).toBeVisible();
    expect((await sheetOf(phone, matchId)).rows).toHaveLength(1);
    await laptop.close();
    await phone.close();
  });
});
