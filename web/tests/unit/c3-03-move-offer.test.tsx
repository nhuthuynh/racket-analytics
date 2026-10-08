// C3-03 (PE-S2-R3-01, major; sprint-03 §5 "S-01 move offer", Gherkin §7.7). Red first, negative
// case first. The server moves only the latest kept rally of a game to the next game and refuses
// any other with 422 validation_failed + decision/not_last_in_game (book.py _check_move_forward,
// PE-S2-R2-01). S-01 must not offer a move the server refuses, must say why, and must explain the
// field code instead of "Try again".
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { ScoreSheetView, type SheetApi } from '@/components/score-sheet/ScoreSheetView';
import { ApiError, createApiClient } from '@/lib/api/client';
import type { Match } from '@/lib/api/types';
import { commandProblem } from '@/lib/tagging/messages';
import type { ScoreSheet, SheetGame, SheetRow } from '@/lib/tagging/types';

const ID = '0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10';
const rid = (n: number) => `7d0c6c1e-3f3a-4c55-9a51-8d1f0e7d2a${String(n).padStart(2, '0')}`;
const match: Match = {
  id: ID, title: 'Saturday doubles', format: 'doubles', status: 'video_received', media: null,
  created_at: 'x', updated_at: 'x', upload: null, rejection: null, participants: [],
};
const row = (n: number, over: Partial<SheetRow> = {}): SheetRow => ({
  rally_id: rid(n), number: n, game: 1, start_ms: n * 1000, end_ms: n * 1000 + 500, serving_side: 'A',
  score_before: '10-0-2', score_after: '11-0-2', winning_side: 'A', ending: 'winner', responsible_player: null,
  fault_kind: null, marker: null, corrected_by_user: false, ...over,
});
const conflict = (n: number, over: Partial<SheetRow> = {}) =>
  row(n, { marker: 'needs_decision', serving_side: null, score_before: null, score_after: null, ...over });
const over1: SheetGame[] = [{ number: 1, first_serving_side: 'A', winner: 'A' }];
const sheet = (rows: SheetRow[], games: SheetGame[] = over1): ScoreSheet => ({
  rules_version: 'PROVISIONAL-UNVERIFIED', unofficial: true, label: 'unofficial scoring (rules not yet verified)',
  rows, games, match_winner: null,
});
const NOT_LAST = new ApiError(422, 'validation_failed', null, { fields: [{ field: 'decision', code: 'not_last_in_game' }] });

function setup(initial: ScoreSheet) {
  const api = {
    undo: vi.fn(), corrections: vi.fn().mockResolvedValue([]), correctRally: vi.fn(), getScoreSheet: vi.fn(),
    rallyMedia: vi.fn(), resolveRally: vi.fn<NonNullable<SheetApi['resolveRally']>>(),
  };
  render(<ScoreSheetView match={match} initialSheet={initial} initialVersion={3} api={api as unknown as SheetApi} />);
  return api;
}

describe('C3-03: "Move to the next game" only on the latest kept rally', () => {
  it('rallies 12 and 13 of 12-14 needing a decision are not offered the next game, and say why', () => {
    setup(sheet([row(11), conflict(12), conflict(13), conflict(14)]));
    for (const n of [12, 13]) {
      const r = screen.getByRole('row', { name: new RegExp(`Rally ${n}\\b`) });
      expect(within(r).queryByRole('button', { name: /to the next game/ })).toBeNull();
      expect(within(r).getByRole('button', { name: `Remove rally ${n}` })).toBeVisible();
      expect(r).toHaveTextContent('Only the last rally of game 1 can move to the next game. Decide rally 14 first.');
    }
  });

  it('the latest kept rally of the game is offered the next game', () => {
    setup(sheet([row(11), conflict(12), conflict(13), conflict(14)]));
    const r14 = screen.getByRole('row', { name: /Rally 14\b/ });
    expect(within(r14).getByRole('button', { name: 'Move rally 14 to the next game' })).toBeVisible();
    expect(r14).not.toHaveTextContent('Only the last rally');
  });

  it('"latest" is by time on the video, not by row number', () => {
    setup(sheet([row(11), conflict(12, { start_ms: 30_000, end_ms: 30_500 }), conflict(13)]));
    expect(within(screen.getByRole('row', { name: /Rally 12\b/ })).getByRole('button', { name: 'Move rally 12 to the next game' })).toBeVisible();
    expect(within(screen.getByRole('row', { name: /Rally 13\b/ })).queryByRole('button', { name: /to the next game/ })).toBeNull();
  });

  it('after the latest rally moves, the next one back is offered the move', async () => {
    const api = setup(sheet([row(11), conflict(12), conflict(13)]));
    api.resolveRally.mockResolvedValueOnce({
      version: 4,
      sheet: sheet([row(11), conflict(12), row(13, { game: 2, score_before: '0-0-2', score_after: '1-0-2' })]),
    });
    await userEvent.click(screen.getByRole('button', { name: 'Move rally 13 to the next game' }));
    expect(await screen.findByRole('button', { name: 'Move rally 12 to the next game' })).toBeVisible();
  });
});

describe('C3-03: decision/not_last_in_game is explained, not "Try again"', () => {
  it('the API client keeps the field code', async () => {
    const fetchFn = vi.fn<typeof fetch>().mockResolvedValueOnce(
      new Response(JSON.stringify({ error: { code: 'validation_failed', support_ref: null, fields: [{ field: 'decision', code: 'not_last_in_game' }] } }), {
        status: 422, headers: { 'content-type': 'application/json' },
      }),
    );
    const client = createApiClient({ baseUrl: '/api', fetch: fetchFn });
    await expect(client.resolveRally(ID, 3, rid(12), 'move_to_next_game')).rejects.toMatchObject({
      code: 'validation_failed', fields: [{ field: 'decision', code: 'not_last_in_game' }],
    });
  });

  it('the message names the rule and never says "Try again"', () => {
    const m = commandProblem(NOT_LAST, 'Decision');
    expect(m).toBe('Only the last rally of a game can move to the next game. Decide the later rallies first.');
    expect(m).not.toMatch(/try again/i);
  });

  it('a refusal from the server (another device moved rallies) shows that message on S-01', async () => {
    const api = setup(sheet([row(11), conflict(12)]));
    api.resolveRally.mockRejectedValueOnce(NOT_LAST);
    await userEvent.click(screen.getByRole('button', { name: 'Move rally 12 to the next game' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Only the last rally of a game can move to the next game.');
  });
});
