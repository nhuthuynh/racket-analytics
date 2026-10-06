// Sprint 2 helpers (QA-owned; QA-ACC, ST-039). Selectors are role/label/text based and use the
// copy the FE ships for T-01 (Quick Tag), K-01 (key map), S-01 (score sheet), H-01 (correction
// history) and V-01 (rally video), until docs/design/flows-sprint-02.md names them (decision-log
// 2026-10-05, FE row). Changing one is a test change (docs/sprints/02/test-change-requests.md).
import { expect, type APIRequestContext, type Page } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { FIXTURE_CLIP, signInByLink } from './sprint-01';

export const UNOFFICIAL = 'unofficial scoring (rules not yet verified)';

/** Ivy (A1, "me") and Dana are side A; Carlos and Sam side B (slot order A1, A2, B1, B2). */
export const PEOPLE = [
  { slot: 'A1', nickname: 'Ivy', is_me: true },
  { slot: 'A2', nickname: 'Dana', is_me: false },
  { slot: 'B1', nickname: 'Carlos', is_me: false },
  { slot: 'B2', nickname: 'Sam', is_me: false },
] as const;
export const MY_SIDE = 'Your side (Ivy and Dana)';
export const OTHER_SIDE = 'Other side (Carlos and Sam)';

export type Ending = 'winner' | 'unforced_error' | 'forced_error' | 'fault' | 'replay';
export interface JourneyTag {
  side: 'mine' | 'other' | null;
  ending: Ending;
  player?: 'Ivy' | 'Dana' | 'Carlos' | 'Sam';
}

/** The 6-rally journey (scripts/measure/taglib.py JOURNEY_TAGS; sprint-02 §12 steps 1-5). */
export const JOURNEY: readonly JourneyTag[] = [
  { side: 'mine', ending: 'winner', player: 'Ivy' },
  { side: 'other', ending: 'unforced_error' },
  { side: 'mine', ending: 'forced_error', player: 'Carlos' },
  { side: 'mine', ending: 'fault', player: 'Sam' },
  { side: null, ending: 'replay' },
  { side: 'mine', ending: 'winner' },
];

/** Reference rows from taglib.expected_rows (independent side-out stepper, provisional preset). */
export const JOURNEY_ROWS = [
  { number: 1, serving_side: 'A', score_before: '0-0-2', score_after: '1-0-2', winning_side: 'A', ending: 'winner' },
  { number: 2, serving_side: 'A', score_before: '1-0-2', score_after: '0-1-1', winning_side: 'B', ending: 'unforced_error' },
  { number: 3, serving_side: 'B', score_before: '0-1-1', score_after: '0-1-2', winning_side: 'A', ending: 'forced_error' },
  { number: 4, serving_side: 'B', score_before: '0-1-2', score_after: '1-0-1', winning_side: 'A', ending: 'fault' },
  { number: 5, serving_side: 'A', score_before: '1-0-1', score_after: '1-0-1', winning_side: null, ending: 'replay' },
  { number: 6, serving_side: 'A', score_before: '1-0-1', score_after: '2-0-1', winning_side: 'A', ending: 'winner' },
] as const;

const ENDING_BUTTON: Record<Ending, string> = {
  winner: 'Winner',
  unforced_error: 'Unforced error',
  forced_error: 'Forced error',
  fault: 'Fault',
  replay: 'Replay',
};
const ENDING_KEY: Record<Ending, string> = { winner: 'w', unforced_error: 'u', forced_error: 'o', fault: 'f', replay: 'r' };
const PLAYER_KEY: Record<string, string> = { Ivy: '3', Dana: '4', Carlos: '5', Sam: '6' };

const TUS = { 'Tus-Resumable': '1.0.0' };

/** Upload the 60 s fixture to ``matchId`` through the web origin (tus core, 2 chunks). */
export async function uploadFixture(request: APIRequestContext, matchId: string): Promise<void> {
  const data = readFileSync(FIXTURE_CLIP);
  const meta = `filename ${Buffer.from('clip.mp4').toString('base64')}`;
  const created = await request.post(`/api/matches/${matchId}/uploads`, {
    headers: { ...TUS, 'Upload-Length': String(data.length), 'Upload-Metadata': meta },
  });
  expect(created.status(), await created.text()).toBe(201);
  const location = created.headers()['location'] ?? '';
  const half = Math.ceil(data.length / 2);
  for (const [at, chunk] of [
    [0, data.subarray(0, half)],
    [half, data.subarray(half)],
  ] as const) {
    const sent = await request.patch(location, {
      headers: { ...TUS, 'Upload-Offset': String(at), 'Content-Type': 'application/offset+octet-stream' },
      data: chunk,
    });
    expect(sent.status(), await sent.text()).toBe(204);
  }
}

/**
 * A fresh account (testing-strategy rule 10) with a doubles match whose video is received.
 * The setup and the upload go through the API of the web origin (the Sprint 1 specs already
 * cover the setup and upload screens); returns the match id.
 */
export async function receivedMatch(
  page: Page,
  title = 'Saturday doubles',
  { signIn = true }: { signIn?: boolean } = {},
): Promise<string> {
  if (signIn) await signInByLink(page);
  const created = await page.request.post('/api/matches', {
    data: { title, format: 'doubles', participants: PEOPLE },
  });
  expect(created.status(), await created.text()).toBe(201);
  const matchId = String(((await created.json()) as { id: string }).id);
  await uploadFixture(page.request, matchId);
  await expect
    .poll(async () => ((await (await page.request.get(`/api/matches/${matchId}`)).json()) as { status: string }).status)
    .toBe('video_received');
  return matchId;
}

/** Open T-01 and start game 1 with Ivy's side serving first. */
export async function openTagging(page: Page, matchId: string): Promise<void> {
  await page.goto(`/matches/${matchId}/tag`);
  await expect(page.getByRole('heading', { level: 1, name: 'Tag rallies' })).toBeVisible();
  const start = page.getByRole('button', { name: 'Start game 1' });
  if (await start.isVisible()) {
    await page.getByRole('radio', { name: MY_SIDE }).check();
    await start.click();
  }
  await expect(page.getByRole('group', { name: 'Tag the rally' })).toBeVisible();
  // Rally times come from the video once it has metadata, from the page clock before: let the
  // video settle first so a rally's start and end never mix the two clocks (SRE-S2-07).
  await expect
    .poll(() => page.evaluate(() => {
      const v = document.querySelector('video');
      return !v || v.readyState > 0 || v.error !== null;
    }), { timeout: 15_000 })
    .toBe(true);
}

/**
 * Give T-01 a video this browser plays (SRE-S2-07, QA-RV2-03). WebKit and a Chrome channel
 * decode the H.264 original, so T-01 reads rally times from the paused video there; Playwright
 * Chromium cannot, so the decodable stand-in is routed to the presigned link and every browser
 * takes the same path. Call before the page opens T-01; WebKit needs `serviceWorkers: 'block'`
 * only when it routes, and it never does (it decodes the original).
 */
export async function playableVideo(page: Page): Promise<void> {
  if (await decodesH264(page)) return;
  const body = await decodableStandIn();
  await page.route(/X-Amz-Signature=/, (route) => route.fulfill(rangeResponse(route.request().headers()['range'], body)));
}

/** Seek the T-01 video (when it plays here) so rally ``i`` (0-based) has its own 10 s slot. */
async function seek(page: Page, seconds: number): Promise<void> {
  await page.evaluate((s) => {
    const v = document.querySelector('video');
    if (v && v.readyState > 0) v.currentTime = s;
  }, seconds);
}

/**
 * Move the rally clock on between "Rally start" and "Rally end" (SRE-S2-07, QA-RV2-03). T-01
 * reads rally times from the video once it has metadata (WebKit, a Chrome channel, or the routed
 * stand-in), so seek it ``seconds`` forward; without a playable video it reads the page clock,
 * so wait until that clock has moved on. Never a fixed sleep: a paused video does not advance.
 */
export async function moveRallyClockOn(page: Page, seconds = 4): Promise<void> {
  await page.evaluate(async (s) => {
    const v = document.querySelector('video');
    if (v && v.readyState > 0) {
      v.currentTime += s;
      return;
    }
    const from = performance.now();
    while (performance.now() - from < 2) await new Promise((r) => setTimeout(r, 1));
  }, seconds);
}

async function waitSaved(page: Page, number: number): Promise<void> {
  await expect(page.getByRole('status').filter({ hasText: new RegExp(`^Rally ${number}:`) }).first()).toBeVisible();
}

/** Tag one rally by taps (T-01 buttons). ``number`` is the rally's 1-based number. */
export async function tagByTaps(page: Page, tag: JourneyTag, number: number): Promise<void> {
  const bar = page.getByRole('group', { name: 'Tag the rally' });
  await seek(page, (number - 1) * 9);
  await bar.getByRole('button', { name: 'Rally start' }).click();
  await seek(page, (number - 1) * 9 + 4);
  await moveRallyClockOn(page, 0); // the seek moved a playable video; else the page clock ticks
  await bar.getByRole('button', { name: 'Rally end' }).click();
  if (tag.side) await bar.getByRole('button', { name: tag.side === 'mine' ? MY_SIDE : OTHER_SIDE }).click();
  if (tag.player) await bar.getByRole('button', { name: tag.player, exact: true }).click();
  await bar.getByRole('button', { name: ENDING_BUTTON[tag.ending], exact: true }).click();
  await waitSaved(page, number);
}

/** Tag one rally with keys only (FR-051, ST-028a): S, then L (5 s on), E, side, player, ending. */
export async function tagByKeys(page: Page, tag: JourneyTag, number: number): Promise<void> {
  await page.keyboard.press('s');
  await page.keyboard.press('l');
  await moveRallyClockOn(page, 0); // L moved a playable video 5 s on; else the page clock ticks
  await page.keyboard.press('e');
  await page.keyboard.press('l');
  if (tag.side) await page.keyboard.press(tag.side === 'mine' ? '1' : '2');
  if (tag.player) await page.keyboard.press(PLAYER_KEY[tag.player] ?? '');
  await page.keyboard.press(ENDING_KEY[tag.ending]);
  await waitSaved(page, number);
}

export interface SheetRowShape {
  number: number;
  rally_id: string;
  serving_side: string | null;
  score_before: string | null;
  score_after: string | null;
  winning_side: string | null;
  ending: string;
  responsible_player: string | null;
  corrected_by_user: boolean;
  marker: string | null;
  start_ms: number;
}
export interface SheetShape {
  rows: SheetRowShape[];
  label: string;
  unofficial: boolean;
}

export async function sheetOf(page: Page, matchId: string): Promise<SheetShape> {
  const r = await page.request.get(`/api/matches/${matchId}/score-sheet`);
  expect(r.status()).toBe(200);
  return (await r.json()) as SheetShape;
}

/** The fields two taggings of the same rallies must agree on (times may differ). */
export function comparable(sheet: SheetShape): unknown[] {
  return sheet.rows.map((r) => ({
    number: r.number,
    serving_side: r.serving_side,
    score_before: r.score_before,
    score_after: r.score_after,
    winning_side: r.winning_side,
    ending: r.ending,
    responsible_player: r.responsible_player,
    marker: r.marker,
  }));
}

export function journeyRows(sheet: SheetShape): unknown[] {
  return sheet.rows.map((r) => ({
    number: r.number,
    serving_side: r.serving_side,
    score_before: r.score_before,
    score_after: r.score_after,
    winning_side: r.winning_side,
    ending: r.ending,
  }));
}

/** Tag the 6-rally journey through the API (for specs that start from a tagged match). */
export async function tagJourneyByApi(page: Page, matchId: string): Promise<void> {
  const slots: Record<string, string> = { Ivy: 'A1', Dana: 'A2', Carlos: 'B1', Sam: 'B2' };
  let version = Number(((await page.request.get(`/api/matches/${matchId}/score-sheet`)).headers()['etag'] ?? '0').replace(/"/g, ''));
  if (version === 0 || (await sheetOf(page, matchId)).rows.length === 0) {
    const games = await page.request.post(`/api/matches/${matchId}/games`, {
      headers: { 'If-Match': `"${version}"` },
      data: { first_serving_side: 'A', ends_switched: false },
    });
    if (games.status() === 201) version = ((await games.json()) as { version: number }).version;
  }
  for (const [i, tag] of JOURNEY.entries()) {
    const r = await page.request.post(`/api/matches/${matchId}/rallies`, {
      headers: { 'If-Match': `"${version}"` },
      data: {
        start_ms: i * 8000,
        end_ms: i * 8000 + 4000,
        winning_side: tag.side === 'mine' ? 'A' : tag.side === 'other' ? 'B' : null,
        ending: tag.ending,
        responsible_player: tag.player ? slots[tag.player] : null,
        fault_kind: null,
      },
    });
    expect(r.status(), await r.text()).toBe(201);
    version = ((await r.json()) as { version: number }).version;
  }
}

/** The page never scrolls sideways at the current viewport (NFR-034, SC 1.4.10). */
export async function expectNoSidewaysScroll(page: Page): Promise<void> {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow, 'page scrolls sideways').toBeLessThanOrEqual(0);
}

/** Every tagging control is at least 48x48 CSS px (NFR-028); message names the offenders. */
export async function expectTaggingTargetsAtLeast48(page: Page): Promise<void> {
  const small = await page.getByRole('group', { name: 'Tag the rally' }).getByRole('button').evaluateAll((els) =>
    els
      .map((el) => {
        const r = el.getBoundingClientRect();
        return { name: (el.textContent ?? '').trim(), w: Math.round(r.width), h: Math.round(r.height) };
      })
      .filter((t) => t.w < 48 || t.h < 48),
  );
  expect(small, `tagging targets below 48x48: ${JSON.stringify(small)}`).toEqual([]);
}

/**
 * A VP9 WebM copy of the fixture (320 px, no audio), made once per machine with ffmpeg. Playwright
 * Chromium has no H.264 decoder (`canPlayType('video/mp4; codecs="avc1.640028"')` is ''), so
 * specs that must see V-01 seek and play in Chromium serve this stand-in for the presigned link;
 * the real link's bytes are covered by IT-02-06 and the API scenario (decision-log 2026-10-06).
 */
export async function decodableStandIn(): Promise<Buffer> {
  const os = await import('node:os');
  const fs = await import('node:fs');
  const { execFileSync } = await import('node:child_process');
  const out = `${os.tmpdir()}/racket-e2e-standin-v1.webm`;
  if (!fs.existsSync(out)) {
    execFileSync('ffmpeg', ['-v', 'error', '-y', '-i', FIXTURE_CLIP, '-vf', 'scale=320:-2', '-r', '30',
      '-c:v', 'libvpx', '-deadline', 'realtime', '-cpu-used', '8', '-b:v', '200k', '-an', `${out}.tmp.webm`]);
    fs.renameSync(`${out}.tmp.webm`, out);
  }
  return fs.readFileSync(out);
}

/** True when this browser can decode the H.264 fixture (WebKit, Chrome; not Playwright Chromium). */
export async function decodesH264(page: Page): Promise<boolean> {
  return page.evaluate(() => document.createElement('video').canPlayType('video/mp4; codecs="avc1.640028"') !== '');
}

/** Serve ``body`` to a media request the way the store does: 206 with Content-Range for a Range. */
export function rangeResponse(
  range: string | undefined,
  body: Buffer,
  contentType = 'video/webm',
): { status: number; headers: Record<string, string>; body: Buffer } {
  const m = /^bytes=(\d*)-(\d*)$/.exec(range ?? '');
  if (!m) {
    return { status: 200, headers: { 'Accept-Ranges': 'bytes', 'Content-Type': contentType }, body };
  }
  const start = m[1] ? Number(m[1]) : Math.max(0, body.length - Number(m[2]));
  const end = m[1] && m[2] ? Math.min(Number(m[2]), body.length - 1) : body.length - 1;
  return {
    status: 206,
    headers: {
      'Accept-Ranges': 'bytes',
      'Content-Type': contentType,
      'Content-Range': `bytes ${start}-${end}/${body.length}`,
    },
    body: body.subarray(start, end + 1),
  };
}
