// Review round 2, FE lane. Red first, negative case first:
// - PD-RV2-01: T-01 notices when its video cannot play (a refused or expired link, or a codec
//   this browser cannot decode), says the rally times will not match the video, and gets a
//   fresh link once when the failure is the link.
// - BE-RV1-FE-01 (a): a Singles match answers rules_unavailable; T-02 says so with no retry.
// - BE-RV1-FE-01 (c): a rally of game n+1 while game n is not over (C-03) is offered
//   "move to game n", not the next game (which the server refuses).
// - PD-FL2-01 / QA-RV2-10: "Switch winner" has an accessible name that starts with its visible
//   words (SC 2.5.3 Label in Name).
import { act, fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { ScoreSheetView, type SheetApi } from '@/components/score-sheet/ScoreSheetView';
import { QuickTag, type QuickTagApi } from '@/components/tagging/QuickTag';
import { ApiError } from '@/lib/api/client';
import type { Match } from '@/lib/api/types';
import type { ScoreSheet, SheetGame, SheetRow } from '@/lib/tagging/types';

const ID = '0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10';
const rid = (n: number) => `7d0c6c1e-3f3a-4c55-9a51-8d1f0e7d2a${String(n).padStart(2, '0')}`;
const match: Match = {
  id: ID, title: 'Saturday doubles', format: 'doubles', status: 'video_received',
  media: { duration_ms: 600_000, width: 1920, height: 1080, fps: 30, video_codec: 'h264', container: 'mp4', size_bytes: 1 } as unknown as Match['media'],
  created_at: 'x', updated_at: 'x', upload: null, rejection: null,
  participants: [{ slot: 'A1', nickname: 'Ivy', is_me: true }, { slot: 'B1', nickname: 'Carlos', is_me: false }],
};
const row = (n: number, over: Partial<SheetRow> = {}): SheetRow => ({
  rally_id: rid(n), number: n, game: 1, start_ms: n * 10_000, end_ms: n * 10_000 + 5000, serving_side: 'A',
  score_before: '0-0-2', score_after: '1-0-2', winning_side: 'A', ending: 'winner', responsible_player: null,
  fault_kind: null, marker: null, corrected_by_user: false, ...over,
});
const conflict = (n: number, game: number) => row(n, { game, marker: 'needs_decision', serving_side: null, score_before: null, score_after: null });
const sheet = (rows: SheetRow[], games: SheetGame[] = [{ number: 1, first_serving_side: 'A', winner: null }]): ScoreSheet => ({
  rules_version: 'PROVISIONAL-UNVERIFIED', unofficial: true, label: 'unofficial scoring (rules not yet verified)',
  rows, games, match_winner: null,
});
const URL1 = 'https://localhost:3000/media/racket-media/a.mp4?X-Amz-Signature=1';
const URL2 = 'https://localhost:3000/media/racket-media/a.mp4?X-Amz-Signature=2';
const NO_VIDEO = /The video cannot be played here right now\. Reload the page to try again\. If you tag without it, the rally times will not match the video\./;

function sheetView(initial: ScoreSheet) {
  const api = {
    undo: vi.fn(), corrections: vi.fn().mockResolvedValue([]), correctRally: vi.fn<SheetApi['correctRally']>(),
    getScoreSheet: vi.fn(), rallyMedia: vi.fn(), resolveRally: vi.fn<NonNullable<SheetApi['resolveRally']>>(),
  };
  render(<ScoreSheetView match={match} initialSheet={initial} initialVersion={3} api={api as unknown as SheetApi} />);
  return api;
}

function quickTag(initial: ScoreSheet, videoSrc: string | null, version = 1) {
  const api = {
    tagRally: vi.fn<QuickTagApi['tagRally']>(), startGame: vi.fn<QuickTagApi['startGame']>(),
    getScoreSheet: vi.fn<QuickTagApi['getScoreSheet']>(), undo: vi.fn<QuickTagApi['undo']>(),
    matchMedia: vi.fn<NonNullable<QuickTagApi['matchMedia']>>(),
  };
  render(<QuickTag match={match} initialSheet={initial} initialVersion={version} api={api} videoSrc={videoSrc} />);
  return api;
}

function failVideo(video: HTMLVideoElement, code: number, message = '') {
  Object.defineProperty(video, 'error', { configurable: true, value: { code, message } });
  act(() => {
    fireEvent(video, new Event('error'));
  });
}

describe('PD-RV2-01: T-01 when its video cannot play', () => {
  it('a codec this browser cannot decode shows the notice and asks for no new link', async () => {
    const api = quickTag(sheet([]), URL1);
    const video = document.querySelector('video')!;
    vi.spyOn(video, 'canPlayType').mockReturnValue('');
    failVideo(video, 3);
    expect(await screen.findByText(/This browser cannot play this video/)).toBeVisible();
    expect(screen.getByText(/the rally times will not match the video/)).toBeVisible();
    expect(api.matchMedia).not.toHaveBeenCalled();
  });

  it('a refused or expired link gets one fresh link, and the notice if that fails too', async () => {
    const api = quickTag(sheet([]), URL1);
    api.matchMedia.mockResolvedValueOnce({ url: URL2, expiresInS: 300, startMs: 0 });
    failVideo(document.querySelector('video')!, 4, 'MEDIA_ELEMENT_ERROR: Format error');
    await vi.waitFor(() => expect(document.querySelector('video')?.getAttribute('src')).toBe(URL2));
    expect(api.matchMedia).toHaveBeenCalledWith(ID);
    expect(screen.queryByText(NO_VIDEO)).toBeNull();
    failVideo(document.querySelector('video')!, 4, 'MEDIA_ELEMENT_ERROR: Format error');
    expect(await screen.findByText(NO_VIDEO)).toBeVisible();
    expect(api.matchMedia).toHaveBeenCalledTimes(1);
  });

  it('a fresh link that cannot be had shows the notice', async () => {
    const api = quickTag(sheet([]), URL1);
    api.matchMedia.mockRejectedValueOnce(new ApiError(500, 'internal_error'));
    failVideo(document.querySelector('video')!, 2);
    expect(await screen.findByText(NO_VIDEO)).toBeVisible();
  });

  it('a link that expires later in a long match is renewed again after the video loaded', async () => {
    const api = quickTag(sheet([]), URL1);
    api.matchMedia
      .mockResolvedValueOnce({ url: URL2, expiresInS: 300, startMs: 0 })
      .mockResolvedValueOnce({ url: URL1, expiresInS: 300, startMs: 0 });
    failVideo(document.querySelector('video')!, 2);
    await vi.waitFor(() => expect(document.querySelector('video')?.getAttribute('src')).toBe(URL2));
    act(() => {
      fireEvent(document.querySelector('video')!, new Event('loadedmetadata'));
    });
    failVideo(document.querySelector('video')!, 2);
    await vi.waitFor(() => expect(api.matchMedia).toHaveBeenCalledTimes(2));
    expect(screen.queryByText(NO_VIDEO)).toBeNull();
  });

  it('a video that failed before the page was hydrated (no error event seen) is still noticed', async () => {
    // Live: the server-rendered <video> fails before React attaches onError (fe-rv2 scratch run).
    const had = Object.getOwnPropertyDescriptor(HTMLMediaElement.prototype, 'error');
    Object.defineProperty(HTMLMediaElement.prototype, 'error', {
      configurable: true,
      get: () => ({ code: 4, message: 'MEDIA_ELEMENT_ERROR: Format error' }),
    });
    try {
      const api = quickTag(sheet([]), URL1);
      api.matchMedia.mockRejectedValueOnce(new ApiError(500, 'internal_error'));
      expect(await screen.findByText(NO_VIDEO)).toBeVisible();
      expect(api.matchMedia).toHaveBeenCalledTimes(1);
    } finally {
      if (had) Object.defineProperty(HTMLMediaElement.prototype, 'error', had);
      else delete (HTMLMediaElement.prototype as { error?: unknown }).error;
    }
  });

  it('no video link at all shows the same notice', () => {
    quickTag(sheet([]), null);
    expect(screen.getByText(NO_VIDEO)).toBeVisible();
  });
});

describe('BE-RV1-FE-01 (a): rules_unavailable on T-02', () => {
  it('"Start game 1" says scoring is not available yet and asks for no retry', async () => {
    const api = quickTag(sheet([], []), null, 0);
    api.startGame.mockRejectedValueOnce(new ApiError(409, 'rules_unavailable', 'ref_0123456789abcdef'));
    await userEvent.click(screen.getByRole('radio', { name: /Your side/ }));
    await userEvent.click(screen.getByRole('button', { name: 'Start game 1' }));
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Scoring for this match format is not available yet.');
    expect(alert).not.toHaveTextContent(/try again/i);
  });
});

describe('BE-RV1-FE-01 (c): C-03, a rally of game 2 while game 1 is not over', () => {
  const games: SheetGame[] = [
    { number: 1, first_serving_side: 'A', winner: null },
    { number: 2, first_serving_side: 'B', winner: null },
  ];

  it('does not offer the next game (the server refuses it); offers game 1 on the first rally of game 2 only', () => {
    sheetView(sheet([row(1), conflict(2, 2), conflict(3, 2)], games));
    const r2 = screen.getByRole('row', { name: /Rally 2/ });
    const r3 = screen.getByRole('row', { name: /Rally 3/ });
    expect(within(r2).queryByRole('button', { name: /to the next game/ })).toBeNull();
    expect(within(r2).getByRole('button', { name: 'Move rally 2 back to game 1' })).toBeVisible();
    expect(within(r2).getByRole('button', { name: 'Remove rally 2' })).toBeVisible();
    expect(within(r3).queryByRole('button', { name: /Move rally 3/ })).toBeNull();
    expect(within(r3).getByRole('button', { name: 'Remove rally 3' })).toBeVisible();
  });

  it('moving back sends move_to_previous_game and says where the rally went', async () => {
    const api = sheetView(sheet([row(1), conflict(2, 2)], games));
    api.resolveRally.mockResolvedValueOnce({ version: 4, sheet: sheet([row(1), row(2)], games) });
    await userEvent.click(screen.getByRole('button', { name: 'Move rally 2 back to game 1' }));
    expect(api.resolveRally).toHaveBeenCalledWith(ID, 3, rid(2), 'move_to_previous_game');
    expect(await screen.findByRole('status')).toHaveTextContent('Rally 2 moved back to game 1.');
  });

  it('a rally after the end of a finished game still offers the next game', () => {
    sheetView(sheet([row(1), conflict(2, 1)], [{ number: 1, first_serving_side: 'A', winner: 'A' }]));
    expect(screen.getByRole('button', { name: 'Move rally 2 to the next game' })).toBeVisible();
    expect(screen.queryByRole('button', { name: /back to game/ })).toBeNull();
  });
});

describe('PD-FL2-01 / QA-RV2-10: Switch winner, SC 2.5.3 Label in Name', () => {
  it('the accessible name starts with the visible words', () => {
    sheetView(sheet([row(1)]));
    const button = screen.getByRole('button', { name: /^Switch winner, rally 1\b/ });
    expect(button).toHaveTextContent('Switch winner');
    expect(button).toHaveAccessibleName('Switch winner, rally 1, to the other side');
  });
});
