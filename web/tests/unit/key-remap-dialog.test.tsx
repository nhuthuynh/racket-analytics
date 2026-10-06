// ST-028b remap in the key map K-01. Negative case first: a used key is refused with a reason and
// nothing changes; Esc cancels without closing the dialog.
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { QuickTag, type QuickTagApi } from '@/components/tagging/QuickTag';
import type { Match } from '@/lib/api/types';
import type { ScoreSheet } from '@/lib/tagging/types';

const match: Match = {
  id: '0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10', title: 'Saturday doubles', format: 'doubles', status: 'video_received',
  media: null, created_at: 'x', updated_at: 'x', upload: null, rejection: null,
  participants: [{ slot: 'A1', nickname: 'Ivy', is_me: true }, { slot: 'B1', nickname: 'Carlos', is_me: false }],
};
const sheet: ScoreSheet = {
  rules_version: 'PROVISIONAL-UNVERIFIED', unofficial: true, label: 'unofficial scoring (rules not yet verified)',
  rows: [], games: [{ number: 1, first_serving_side: 'A', winner: null }], match_winner: null,
};

afterEach(() => localStorage.clear());

function setup() {
  const api = { tagRally: vi.fn(() => new Promise(() => {})), startGame: vi.fn(), getScoreSheet: vi.fn(), undo: vi.fn() };
  render(<QuickTag match={match} initialSheet={sheet} initialVersion={1} api={api as unknown as QuickTagApi} clock={() => 0} videoSrc={null} />);
}

describe('remap keys in K-01 (ST-028b)', () => {
  it('a used key is refused with the reason; Esc cancels and keeps the dialog open', async () => {
    const u = userEvent.setup();
    setup();
    await u.keyboard('?');
    const dialog = screen.getByRole('dialog', { name: 'Keyboard shortcuts' });
    await u.selectOptions(within(dialog).getByRole('combobox', { name: 'Shortcut to change' }), 'Rally start');
    await u.click(within(dialog).getByRole('button', { name: 'Choose a new key' }));
    expect(within(dialog).getByText('Press the new key for Rally start. Esc cancels.')).toBeVisible();
    await u.keyboard('e');
    expect(within(dialog).getByRole('alert')).toHaveTextContent('E is already used for Rally end.');
    await u.click(within(dialog).getByRole('button', { name: 'Choose a new key' }));
    await u.keyboard('{Escape}');
    expect(screen.getByRole('dialog', { name: 'Keyboard shortcuts' })).toBeInTheDocument();
    expect(within(dialog).getByRole('row', { name: 'S Rally start' })).toBeInTheDocument();
  });

  it('a new key works at once, the old one stops, and it is remembered; reset brings the defaults back', async () => {
    const u = userEvent.setup();
    setup();
    await u.keyboard('?');
    const dialog = screen.getByRole('dialog', { name: 'Keyboard shortcuts' });
    await u.selectOptions(within(dialog).getByRole('combobox', { name: 'Shortcut to change' }), 'Rally start');
    await u.click(within(dialog).getByRole('button', { name: 'Choose a new key' }));
    await u.keyboard('a');
    expect(within(dialog).getByRole('status')).toHaveTextContent('Rally start is now A.');
    expect(JSON.parse(localStorage.getItem('racket.tagging.keymap')!).mark_start).toBe('a');
    await u.click(within(dialog).getByRole('button', { name: 'Close' }));
    await u.keyboard('s');
    expect(screen.getByRole('button', { name: 'Rally start' })).toHaveAttribute('aria-pressed', 'false');
    await u.keyboard('a');
    expect(screen.getByRole('button', { name: 'Rally start' })).toHaveAttribute('aria-pressed', 'true');
    await u.keyboard('?');
    await u.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Use the default keys' }));
    expect(within(screen.getByRole('dialog')).getByRole('row', { name: 'S Rally start' })).toBeInTheDocument();
  });
});
