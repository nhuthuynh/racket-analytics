// ST-027 FE slice 3: the Quick Tag screen (T-01). Tapping only; the API is a fake. Negative
// cases first: no game started, a server error rolls back, a stale version, a finished game.
import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { QuickTag, type QuickTagApi } from '@/components/tagging/QuickTag';
import { ApiError } from '@/lib/api/client';
import type { Match } from '@/lib/api/types';
import type { ScoreSheet, SheetRow } from '@/lib/tagging/types';

const ID = '0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10';
const R1 = '7d0c6c1e-3f3a-4c55-9a51-8d1f0e7d2a10';
const match: Match = {
  id: ID, title: 'Saturday doubles', format: 'doubles', status: 'video_received', media: null,
  created_at: 'x', updated_at: 'x', upload: null, rejection: null,
  participants: [
    { slot: 'A1', nickname: 'Ivy', is_me: true }, { slot: 'A2', nickname: 'Dana', is_me: false },
    { slot: 'B1', nickname: 'Carlos', is_me: false }, { slot: 'B2', nickname: 'Bo', is_me: false },
  ],
};
const LABEL = 'unofficial scoring (rules not yet verified)';
const sheet = (rows: SheetRow[] = [], games: ScoreSheet['games'] = [{ number: 1, first_serving_side: 'A', winner: null }]): ScoreSheet => ({
  rules_version: 'PROVISIONAL-UNVERIFIED', unofficial: true, label: LABEL, rows, games, match_winner: null,
});
const row1: SheetRow = {
  rally_id: R1, number: 1, game: 1, start_ms: 1000, end_ms: 5000, serving_side: 'A', score_before: '0-0-2',
  score_after: '1-0-2', winning_side: 'A', ending: 'winner', responsible_player: null, fault_kind: null, marker: null, corrected_by_user: false,
};

function deferred<T>() {
  let resolve!: (v: T) => void;
  let reject!: (e: unknown) => void;
  const promise = new Promise<T>((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
}

function setup(initial: ScoreSheet = sheet(), version = 1) {
  const api = {
    tagRally: vi.fn<QuickTagApi['tagRally']>(),
    startGame: vi.fn<QuickTagApi['startGame']>(),
    getScoreSheet: vi.fn<QuickTagApi['getScoreSheet']>(),
    undo: vi.fn<QuickTagApi['undo']>(),
  };
  let t = 1000;
  const clock = () => t;
  const setTime = (ms: number) => { t = ms; };
  render(<QuickTag match={match} initialSheet={initial} initialVersion={version} api={api} clock={clock} videoSrc={null} />);
  return { api, setTime };
}

const user = () => userEvent.setup();

async function markRally(u: ReturnType<typeof user>, setTime: (ms: number) => void, from: number, to: number) {
  setTime(from);
  await u.click(screen.getByRole('button', { name: 'Rally start' }));
  setTime(to);
  await u.click(screen.getByRole('button', { name: 'Rally end' }));
}

describe('QuickTag (T-01)', () => {
  it('asks who serves first before game 1 and tags nothing until the game is started', async () => {
    const { api } = setup(sheet([], []), 0);
    expect(screen.queryByRole('button', { name: 'Rally start' })).toBeNull();
    const u = user();
    await u.click(screen.getByRole('radio', { name: 'Your side (Ivy and Dana)' }));
    api.startGame.mockResolvedValueOnce({ version: 1, sheet: sheet() });
    await u.click(screen.getByRole('button', { name: 'Start game 1' }));
    expect(api.startGame).toHaveBeenCalledWith(ID, 0, { first_serving_side: 'A', ends_switched: false });
    expect(await screen.findByRole('button', { name: 'Rally start' })).toBeVisible();
    expect(screen.getByText('0-0-2')).toBeVisible();
  });

  it('PD-S2R1-06: before game 1 starts it shows no call and no server, only the question', () => {
    setup(sheet([], []), 0);
    expect(screen.getByText('Who serves first in game 1?')).toBeVisible();
    expect(screen.queryByText('0-0-2')).toBeNull();
    expect(screen.queryByText('Your side serves')).toBeNull();
    expect(screen.queryByText('Other side serves')).toBeNull();
  });

  it('a tag shows the optimistic score at once, then the server sheet', async () => {
    const { api, setTime } = setup();
    const answer = deferred<Awaited<ReturnType<QuickTagApi['tagRally']>>>();
    api.tagRally.mockReturnValueOnce(answer.promise);
    const u = user();
    await markRally(u, setTime, 1000, 5000);
    await u.click(screen.getByRole('button', { name: /^Your side/ }));
    await u.click(screen.getByRole('button', { name: 'Winner' }));
    expect(api.tagRally).toHaveBeenCalledWith(ID, 1, {
      start_ms: 1000, end_ms: 5000, winning_side: 'A', ending: 'winner', responsible_player: null, fault_kind: null,
    });
    const score = screen.getByRole('group', { name: 'Score' });
    expect(within(score).getByText('1-0-2')).toBeVisible();
    expect(within(score).getByText('Saving…')).toBeVisible();
    await act(async () => answer.resolve({ version: 2, rallyId: R1, sheet: sheet([row1]) }));
    expect(within(score).queryByText('Saving…')).toBeNull();
    expect(screen.getByText('Rally 1: us. Score 1-0-2.')).toBeVisible();
  });

  it('records the responsible player and lets the player be cleared', async () => {
    const { api, setTime } = setup();
    api.tagRally.mockResolvedValueOnce({ version: 2, rallyId: R1, sheet: sheet([{ ...row1, winning_side: 'B', ending: 'unforced_error', responsible_player: 'A1', score_after: '0-0-1' }]) });
    const u = user();
    await markRally(u, setTime, 1000, 5000);
    await u.click(screen.getByRole('button', { name: /^Other side/ }));
    await u.click(screen.getByRole('button', { name: 'Dana' }));
    expect(screen.getByRole('button', { name: 'Dana' })).toHaveAttribute('aria-pressed', 'true');
    await u.click(screen.getByRole('button', { name: 'Dana' }));
    expect(screen.getByRole('button', { name: 'Dana' })).toHaveAttribute('aria-pressed', 'false');
    await u.click(screen.getByRole('button', { name: 'Ivy' }));
    await u.click(screen.getByRole('button', { name: 'Unforced error' }));
    expect(api.tagRally.mock.calls[0]![2]).toMatchObject({ winning_side: 'B', responsible_player: 'A1', ending: 'unforced_error' });
  });

  it('a server error rolls the score back, keeps the marks and says what happened', async () => {
    const { api, setTime } = setup();
    api.tagRally.mockRejectedValueOnce(new ApiError(500, 'internal_error', 'ref_0123456789abcdef'));
    const u = user();
    await markRally(u, setTime, 1000, 5000);
    await u.click(screen.getByRole('button', { name: /^Your side/ }));
    await u.click(screen.getByRole('button', { name: 'Winner' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('The rally was not saved. Try again. Reference: ref_0123456789abcdef');
    const score = screen.getByRole('group', { name: 'Score' });
    expect(within(score).getByText('0-0-2')).toBeVisible();
    expect(screen.getByRole('button', { name: /^Your side/ })).toHaveAttribute('aria-pressed', 'true');
    api.tagRally.mockResolvedValueOnce({ version: 2, rallyId: R1, sheet: sheet([row1]) });
    await u.click(screen.getByRole('button', { name: 'Winner' }));
    expect(api.tagRally).toHaveBeenCalledTimes(2);
  });

  it('a stale version shows the latest score and says the match changed', async () => {
    const { api, setTime } = setup();
    api.tagRally.mockRejectedValueOnce(new ApiError(409, 'stale_match'));
    api.getScoreSheet.mockResolvedValueOnce({ version: 5, sheet: sheet([row1]) });
    const u = user();
    await markRally(u, setTime, 6000, 9000);
    await u.click(screen.getByRole('button', { name: /^Your side/ }));
    await u.click(screen.getByRole('button', { name: 'Winner' }));
    expect(await screen.findByText(/changed on another device/)).toBeVisible();
    expect(within(screen.getByRole('group', { name: 'Score' })).getByText('1-0-2')).toBeVisible();
  });

  it('a wrong-side player is refused before anything is sent', async () => {
    const { api, setTime } = setup();
    const u = user();
    await markRally(u, setTime, 1000, 5000);
    await u.click(screen.getByRole('button', { name: /^Your side/ }));
    await u.click(screen.getByRole('button', { name: 'Dana' }));
    await u.click(screen.getByRole('button', { name: 'Unforced error' }));
    expect(api.tagRally).not.toHaveBeenCalled();
    expect(screen.getByRole('alert')).toHaveTextContent('The player who made the error must be on the side that lost the rally.');
  });

  it('when the server says the game is over it offers the next game', async () => {
    const { api, setTime } = setup();
    api.tagRally.mockRejectedValueOnce(new ApiError(409, 'game_over'));
    api.getScoreSheet.mockResolvedValueOnce({ version: 9, sheet: sheet([row1], [{ number: 1, first_serving_side: 'A', winner: 'A' }]) });
    const u = user();
    await markRally(u, setTime, 6000, 9000);
    await u.click(screen.getByRole('button', { name: /^Your side/ }));
    await u.click(screen.getByRole('button', { name: 'Winner' }));
    expect(await screen.findByRole('button', { name: 'Start game 2' })).toBeVisible();
    expect(screen.getByText('Game 1 won by your side.')).toBeVisible();
  });

  it('a finished match offers the score sheet and no controls', () => {
    setup({ ...sheet([row1], [{ number: 1, first_serving_side: 'A', winner: 'A' }, { number: 2, first_serving_side: 'B', winner: 'A' }]), match_winner: 'A' });
    expect(screen.getByText('Match won by your side.')).toBeVisible();
    expect(screen.queryByRole('button', { name: 'Rally start' })).toBeNull();
    expect(screen.getByRole('link', { name: 'Open the score sheet' })).toHaveAttribute('href', `/matches/${ID}/sheet`);
  });

  it('labels the score as unofficial', () => {
    setup();
    expect(screen.getByText(LABEL)).toBeVisible();
  });
});
