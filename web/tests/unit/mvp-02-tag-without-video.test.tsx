// MVP-02 (FR-050; live finding on main 6c666b9): T-01 offers tagging without the video when the
// browser cannot play it, but only rally 1 was saved. The <video> had metadata (readyState > 0)
// and a media error, so its time stayed at 0 and every later "Rally start" was refused.
// Component + reducer + rally clock together, the API faked. Negative case first.
import { act, fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { QuickTag, type QuickTagApi } from '@/components/tagging/QuickTag';
import { ApiError } from '@/lib/api/client';
import type { Match } from '@/lib/api/types';
import type { ScoreSheet, SheetRow, TagInput } from '@/lib/tagging/types';

const ID = '0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10';
const match: Match = {
  id: ID, title: 'Saturday doubles', format: 'doubles', status: 'video_received',
  media: { duration_ms: 600_000, width: 1920, height: 1080, fps: 30, video_codec: 'h264', container: 'mp4', size_bytes: 1 } as unknown as Match['media'],
  created_at: 'x', updated_at: 'x', upload: null, rejection: null,
  participants: [{ slot: 'A1', nickname: 'Ivy', is_me: true }, { slot: 'B1', nickname: 'Carlos', is_me: false }],
};
const URL1 = 'https://localhost:3000/media/racket-media/a.mp4?X-Amz-Signature=1';
const sheet = (rows: SheetRow[]): ScoreSheet => ({
  rules_version: 'PROVISIONAL-UNVERIFIED', unofficial: true, label: 'unofficial scoring (rules not yet verified)',
  rows, games: [{ number: 1, first_serving_side: 'A', winner: null }], match_winner: null,
});

let page = 0;
const NO_TIME_LEFT =
  'The rally times have reached the end of the video, so no more rallies can be tagged without it.';
afterEach(() => vi.restoreAllMocks());

/** T-01 with a server that saves every tag it is sent, as the API does; like the scorebook
 *  (I-within), it refuses with 422 time_after_video a rally that ends after the video. */
function quickTag(initial: SheetRow[] = []) {
  const rows = [...initial];
  const api = {
    tagRally: vi.fn<QuickTagApi['tagRally']>(async (_id, version, tag: TagInput) => {
      if (tag.end_ms > match.media!.duration_ms) {
        throw new ApiError(422, 'invalid_rally', null, { fields: [{ field: 'end_ms', code: 'time_after_video' }] });
      }
      const n = rows.length + 1;
      rows.push({
        rally_id: `7d0c6c1e-3f3a-4c55-9a51-8d1f0e7d2a${String(n).padStart(2, '0')}`, number: n, game: 1,
        start_ms: tag.start_ms, end_ms: tag.end_ms, serving_side: 'A', score_before: '0-0-2', score_after: `${n}-0-2`,
        winning_side: tag.winning_side, ending: tag.ending, responsible_player: null, fault_kind: null, marker: null,
        corrected_by_user: false,
      });
      return { version: version + 1, rallyId: rows[n - 1]!.rally_id, sheet: sheet([...rows]) };
    }),
    startGame: vi.fn<QuickTagApi['startGame']>(), getScoreSheet: vi.fn<QuickTagApi['getScoreSheet']>(),
    undo: vi.fn<QuickTagApi['undo']>(), matchMedia: vi.fn<NonNullable<QuickTagApi['matchMedia']>>(),
  };
  vi.spyOn(performance, 'now').mockImplementation(() => page);
  render(<QuickTag match={match} initialSheet={sheet(initial)} initialVersion={1} api={api} videoSrc={URL1} />);
  return api;
}

/** The live case: metadata loaded (readyState 1), the time stuck at 0, then a decode error. */
function videoThatCannotPlay(): HTMLVideoElement {
  const video = document.querySelector('video')!;
  Object.defineProperty(video, 'readyState', { configurable: true, get: () => 1 });
  Object.defineProperty(video, 'currentTime', { configurable: true, get: () => 0, set: () => {} });
  vi.spyOn(video, 'canPlayType').mockReturnValue('');
  Object.defineProperty(video, 'error', { configurable: true, value: { code: 3, message: '' } });
  act(() => {
    fireEvent(video, new Event('error'));
  });
  return video;
}

async function tagRally(u: ReturnType<typeof userEvent.setup>, n: number) {
  page += 2_000;
  await u.click(screen.getByRole('button', { name: 'Rally start' }));
  expect(screen.queryByRole('alert')?.textContent ?? null, `rally ${n} start`).toBeNull();
  page += 4_000;
  await u.click(screen.getByRole('button', { name: 'Rally end' }));
  expect(screen.queryByRole('alert')?.textContent ?? null, `rally ${n} end`).toBeNull();
  await u.click(screen.getByRole('button', { name: /^Your side/ }));
  await u.click(screen.getByRole('button', { name: 'Winner' }));
  expect(await screen.findByText(new RegExp(`^Rally ${n}: us\\.`))).toBeInTheDocument();
}

describe('MVP-02: tagging without a playable video', () => {
  it('a later "Rally start" is not refused as before the end of the last rally', async () => {
    quickTag();
    videoThatCannotPlay();
    expect(await screen.findByText(/This browser cannot play this video/)).toBeVisible();
    const u = userEvent.setup();
    await tagRally(u, 1);
    page += 2_000;
    await u.click(screen.getByRole('button', { name: 'Rally start' }));
    expect(screen.queryByText(/This rally starts before the end of rally 1/)).toBeNull();
    expect(screen.getByRole('button', { name: 'Rally start' })).toHaveAttribute('aria-pressed', 'true');
  });

  it('three rallies tagged without the video are all sent, each after the one before', async () => {
    const api = quickTag();
    videoThatCannotPlay();
    const u = userEvent.setup();
    for (const n of [1, 2, 3]) await tagRally(u, n);
    expect(api.tagRally).toHaveBeenCalledTimes(3);
    const tags = api.tagRally.mock.calls.map((c) => c[2]);
    for (const [i, t] of tags.entries()) {
      expect(t.end_ms).toBeGreaterThan(t.start_ms);
      if (i > 0) expect(t.start_ms).toBeGreaterThanOrEqual(tags[i - 1]!.end_ms);
    }
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('carries on after rallies tagged earlier from the video (their times are later than the page clock)', async () => {
    const earlier: SheetRow = {
      rally_id: '7d0c6c1e-3f3a-4c55-9a51-8d1f0e7d2a01', number: 1, game: 1, start_ms: 300_000, end_ms: 305_000,
      serving_side: 'A', score_before: '0-0-2', score_after: '1-0-2', winning_side: 'A', ending: 'winner',
      responsible_player: null, fault_kind: null, marker: null, corrected_by_user: false,
    };
    const api = quickTag([earlier]);
    videoThatCannotPlay();
    const u = userEvent.setup();
    await tagRally(u, 2);
    expect(api.tagRally.mock.calls[0]![2].start_ms).toBeGreaterThanOrEqual(305_000);
  });

  it('a video that plays still gives the rally times (unchanged behaviour)', async () => {
    const api = quickTag();
    const video = document.querySelector('video')!;
    let time = 0;
    Object.defineProperty(video, 'readyState', { configurable: true, get: () => 1 });
    Object.defineProperty(video, 'currentTime', { configurable: true, get: () => time, set: (s: number) => { time = s; } });
    const u = userEvent.setup();
    time = 12;
    await u.click(screen.getByRole('button', { name: 'Rally start' }));
    time = 16.5;
    await u.click(screen.getByRole('button', { name: 'Rally end' }));
    await u.click(screen.getByRole('button', { name: /^Your side/ }));
    await u.click(screen.getByRole('button', { name: 'Winner' }));
    await vi.waitFor(() => expect(api.tagRally).toHaveBeenCalledTimes(1));
    expect(api.tagRally.mock.calls[0]![2]).toMatchObject({ start_ms: 12_000, end_ms: 16_500 });
  });

  // PE-MVP02-R1-01: the page clock carries on from rallies tagged from the video, so near the
  // end of the video it would pass the duration and every later rally would be refused.
  const earlierAt = (start: number, end: number): SheetRow => ({
    rally_id: '7d0c6c1e-3f3a-4c55-9a51-8d1f0e7d2a01', number: 1, game: 1, start_ms: start, end_ms: end,
    serving_side: 'A', score_before: '0-0-2', score_after: '1-0-2', winning_side: 'A', ending: 'winner',
    responsible_player: null, fault_kind: null, marker: null, corrected_by_user: false,
  });

  it('near the end of the video no rally is refused as ending after the video (422 time_after_video)', async () => {
    const api = quickTag([earlierAt(590_000, 597_000)]);
    videoThatCannotPlay();
    const u = userEvent.setup();
    for (const n of [2, 3, 4]) await tagRally(u, n);
    expect(screen.queryByText(/ends after the end of the video/)).toBeNull();
    const tags = api.tagRally.mock.calls.map((c) => c[2]);
    expect(tags).toHaveLength(3);
    for (const t of tags) expect(t.end_ms).toBeLessThanOrEqual(600_000);
  });

  it('when no time is left in the video, says so and sends nothing', async () => {
    const api = quickTag([earlierAt(595_000, 600_000)]);
    videoThatCannotPlay();
    const u = userEvent.setup();
    page += 2_000;
    await u.click(screen.getByRole('button', { name: 'Rally start' }));
    expect(screen.getByRole('alert')).toHaveTextContent(NO_TIME_LEFT);
    expect(screen.getByRole('button', { name: 'Rally start' })).toHaveAttribute('aria-pressed', 'false');
    expect(api.tagRally).not.toHaveBeenCalled();
  });
});
