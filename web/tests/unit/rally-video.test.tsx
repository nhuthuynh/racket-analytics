// ST-037 FE: every rally row opens the video at that rally through a short-lived link (FR-027;
// NFR-055). Negative cases first: a link that cannot be had, and a link that stopped working
// (expired or changed) say so, and choosing the rally again fetches a fresh link.
import { act, fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { ScoreSheetView, type SheetApi } from '@/components/score-sheet/ScoreSheetView';
import { ApiError } from '@/lib/api/client';
import type { Match } from '@/lib/api/types';
import type { ScoreSheet, SheetRow } from '@/lib/tagging/types';

const ID = '0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10';
const rid = (n: number) => `7d0c6c1e-3f3a-4c55-9a51-8d1f0e7d2a${String(n).padStart(2, '0')}`;
const match: Match = {
  id: ID, title: 'Saturday doubles', format: 'doubles', status: 'video_received', media: null,
  created_at: 'x', updated_at: 'x', upload: null, rejection: null, participants: [],
};
const row = (n: number, over: Partial<SheetRow> = {}): SheetRow => ({
  rally_id: rid(n), number: n, game: 1, start_ms: 872_000, end_ms: 880_000, serving_side: 'A',
  score_before: '0-0-2', score_after: '1-0-2', winning_side: 'A', ending: 'winner', responsible_player: null,
  fault_kind: null, marker: null, corrected_by_user: false, ...over,
});
const sheet: ScoreSheet = {
  rules_version: 'PROVISIONAL-UNVERIFIED', unofficial: true, label: 'unofficial scoring (rules not yet verified)',
  rows: [row(12)], games: [{ number: 1, first_serving_side: 'A', winner: null }], match_winner: null,
};
const URL1 = 'https://localhost:3000/media/racket-media/a.mp4?X-Amz-Signature=1';
const URL2 = 'https://localhost:3000/media/racket-media/a.mp4?X-Amz-Signature=2';

function setup() {
  const api = {
    undo: vi.fn(), corrections: vi.fn().mockResolvedValue([]), correctRally: vi.fn(), getScoreSheet: vi.fn(),
    rallyMedia: vi.fn<SheetApi['rallyMedia']>(),
  };
  render(<ScoreSheetView match={match} initialSheet={sheet} initialVersion={1} api={api as unknown as SheetApi} />);
  return api;
}

describe('rally video V-01 (ST-037)', () => {
  it('says so when the link cannot be had', async () => {
    const api = setup();
    api.rallyMedia.mockRejectedValueOnce(new ApiError(500, 'internal_error', 'ref_0123456789abcdef'));
    await userEvent.click(screen.getByRole('button', { name: 'Watch rally 12' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('The video for rally 12 could not be opened. Try again. Reference: ref_0123456789abcdef');
  });

  it('opens the video at the rally start from a fresh short-lived link', async () => {
    const api = setup();
    api.rallyMedia.mockResolvedValueOnce({ url: URL1, expiresInS: 600, startMs: 872_000 });
    await userEvent.click(screen.getByRole('button', { name: 'Watch rally 12' }));
    expect(api.rallyMedia).toHaveBeenCalledWith(ID, rid(12));
    const region = await screen.findByRole('region', { name: 'Rally 12 video' });
    const video = region.querySelector('video')!;
    expect(video.getAttribute('src')).toBe(URL1);
    const play = vi.spyOn(video, 'play').mockResolvedValue();
    act(() => {
      fireEvent(video, new Event('loadedmetadata'));
    });
    expect(video.currentTime).toBe(872);
    expect(play).toHaveBeenCalled();
    expect(screen.getByText('Starts at 14:32')).toBeVisible();
  });

  it('a link that stopped working says so, and choosing the rally again gets a new one', async () => {
    const api = setup();
    api.rallyMedia.mockResolvedValueOnce({ url: URL1, expiresInS: 600, startMs: 872_000 }).mockResolvedValueOnce({ url: URL2, expiresInS: 600, startMs: 872_000 });
    await userEvent.click(screen.getByRole('button', { name: 'Watch rally 12' }));
    const video = (await screen.findByRole('region', { name: 'Rally 12 video' })).querySelector('video')!;
    act(() => {
      fireEvent(video, new Event('error'));
    });
    expect(screen.getByRole('alert')).toHaveTextContent("This video link no longer works. Choose 'Watch rally 12' again.");
    await userEvent.click(screen.getByRole('button', { name: 'Watch rally 12' }));
    expect((await screen.findByRole('region', { name: 'Rally 12 video' })).querySelector('video')!.getAttribute('src')).toBe(URL2);
  });

  it('never puts the media URL in a link the player could copy into the page', () => {
    setup();
    expect(document.querySelector('a[href*="X-Amz"]')).toBeNull();
  });
});
