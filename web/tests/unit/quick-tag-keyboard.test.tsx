// ST-028a keyboard tagging on T-01 and the key map K-01 (FR-051; sprint-02 §7.1 "Keyboard
// tagging"). Negative case first: with single-key shortcuts off, "1" records no winner.
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { QuickTag, type QuickTagApi } from '@/components/tagging/QuickTag';
import type { Match } from '@/lib/api/types';
import type { ScoreSheet } from '@/lib/tagging/types';

const ID = '0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10';
const match: Match = {
  id: ID, title: 'Saturday doubles', format: 'doubles', status: 'video_received', media: null,
  created_at: 'x', updated_at: 'x', upload: null, rejection: null,
  participants: [
    { slot: 'A1', nickname: 'Ivy', is_me: true }, { slot: 'A2', nickname: 'Dana', is_me: false },
    { slot: 'B1', nickname: 'Carlos', is_me: false }, { slot: 'B2', nickname: 'Bo', is_me: false },
  ],
};
const sheet: ScoreSheet = {
  rules_version: 'PROVISIONAL-UNVERIFIED', unofficial: true, label: 'unofficial scoring (rules not yet verified)',
  rows: [], games: [{ number: 1, first_serving_side: 'A', winner: null }], match_winner: null,
};

afterEach(() => localStorage.clear());

function setup() {
  const api = { tagRally: vi.fn<QuickTagApi['tagRally']>(), startGame: vi.fn(), getScoreSheet: vi.fn(), undo: vi.fn() };
  api.tagRally.mockReturnValue(new Promise(() => {}));
  let t = 1000;
  render(<QuickTag match={match} initialSheet={sheet} initialVersion={1} api={api as unknown as QuickTagApi} clock={() => t} videoSrc={null} />);
  return { api, setTime: (ms: number) => { t = ms; } };
}

describe('Keyboard tagging (ST-028a)', () => {
  it('with single-key shortcuts off, "1" records no winner', async () => {
    const u = userEvent.setup();
    setup();
    await u.click(screen.getByRole('button', { name: 'Keyboard shortcuts' }));
    const dialog = screen.getByRole('dialog', { name: 'Keyboard shortcuts' });
    await u.click(within(dialog).getByRole('checkbox', { name: 'Use single-key shortcuts' }));
    await u.click(within(dialog).getByRole('button', { name: 'Close' }));
    await u.keyboard('1');
    expect(screen.getByRole('button', { name: /^Your side/ })).toHaveAttribute('aria-pressed', 'false');
    expect(localStorage.getItem('racket.tagging.single-keys')).toBe('off');
  });

  it('tags a rally with keys only, with the same body as tapping', async () => {
    const u = userEvent.setup();
    const { api, setTime } = setup();
    setTime(1000);
    await u.keyboard('s');
    setTime(5000);
    await u.keyboard('e');
    await u.keyboard('2');
    await u.keyboard('3');
    await u.keyboard('u');
    expect(api.tagRally).toHaveBeenCalledWith(ID, 1, {
      start_ms: 1000, end_ms: 5000, winning_side: 'B', ending: 'unforced_error', responsible_player: 'A1', fault_kind: null,
    });
  });

  it('Esc clears the marks', async () => {
    const u = userEvent.setup();
    setup();
    await u.keyboard('s');
    expect(screen.getByRole('button', { name: 'Rally start' })).toHaveAttribute('aria-pressed', 'true');
    await u.keyboard('{Escape}');
    expect(screen.getByRole('button', { name: 'Rally start' })).toHaveAttribute('aria-pressed', 'false');
  });

  it('"?" shows every shortcut and what it does; closing returns focus', async () => {
    const u = userEvent.setup();
    setup();
    const start = screen.getByRole('button', { name: 'Rally start' });
    start.focus();
    await u.keyboard('?');
    const dialog = screen.getByRole('dialog', { name: 'Keyboard shortcuts' });
    const table = within(dialog).getByRole('table', { name: 'Tagging shortcuts' });
    expect(within(table).getByRole('row', { name: 'S Rally start' })).toBeInTheDocument();
    expect(within(table).getByRole('row', { name: '3 Player: Ivy' })).toBeInTheDocument();
    expect(within(table).getByRole('row', { name: 'Space Play or pause the video' })).toBeInTheDocument();
    await u.click(within(dialog).getByRole('button', { name: 'Close' }));
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(start).toHaveFocus();
  });

  it('PD-S2R1-04: "?" pressed with nothing focused returns focus to "Keyboard shortcuts", not the page body', async () => {
    const u = userEvent.setup();
    setup();
    (document.activeElement as HTMLElement | null)?.blur();
    await u.keyboard('?');
    const dialog = screen.getByRole('dialog', { name: 'Keyboard shortcuts' });
    // jsdom does not turn Esc into the dialog's cancel event; the Esc path is covered in Chromium (E2E).
    await u.click(within(dialog).getByRole('button', { name: 'Close' }));
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(screen.getByRole('button', { name: 'Keyboard shortcuts' })).toHaveFocus();
  });

  it('keys typed in the dialog checkbox do not tag', async () => {
    const u = userEvent.setup();
    setup();
    await u.keyboard('?');
    await u.keyboard('s');
    expect(screen.getByRole('button', { name: 'Rally start' })).toHaveAttribute('aria-pressed', 'false');
  });
});
