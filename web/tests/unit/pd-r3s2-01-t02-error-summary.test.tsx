// PD-R3S2-01 (minor, Sprint 2 review round 3 carry-over; sprint-03 C3-10): T-02 "Who serves first
// in game n?" shows its errors as the shared error summary [DPA/DESIGN-13]: heading "There is a
// problem", focus moves to it, a link per field moves focus to the question, the question shows
// the message inline and names it. Red first, negative case first.
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { GameStartForm } from '@/components/tagging/GameStartForm';

const label = (s: 'A' | 'B') => (s === 'A' ? 'Your side (Ivy and Dana)' : 'Other side (Carlos and Bo)');

describe('PD-R3S2-01: T-02 error summary', () => {
  it('no choice: the summary has the heading, takes focus and links to the question', async () => {
    const onStart = vi.fn();
    render(<GameStartForm game={2} mySide="A" label={label} onStart={onStart} />);
    await userEvent.click(screen.getByRole('button', { name: 'Start game 2' }));
    expect(onStart).not.toHaveBeenCalled();
    const summary = screen.getByRole('alert');
    expect(within(summary).getByRole('heading', { name: 'There is a problem' })).toBeVisible();
    expect(summary).toHaveFocus();
    await userEvent.click(within(summary).getByRole('link', { name: 'Choose who serves first in game 2.' }));
    expect(screen.getByRole('radio', { name: 'Your side (Ivy and Dana)' })).toHaveFocus();
  });

  it('no choice: the question shows the message inline and is described by it', async () => {
    render(<GameStartForm game={2} mySide="A" label={label} onStart={vi.fn()} />);
    await userEvent.click(screen.getByRole('button', { name: 'Start game 2' }));
    const group = screen.getByRole('group', { name: 'Who serves first in game 2?' });
    expect(group).toHaveAccessibleDescription('Error: Choose who serves first in game 2.');
  });

  it('pressing Start again with no choice moves focus back to the summary', async () => {
    render(<GameStartForm game={3} mySide="A" label={label} onStart={vi.fn()} />);
    const start = screen.getByRole('button', { name: 'Start game 3' });
    await userEvent.click(start);
    start.focus();
    await userEvent.click(start);
    expect(screen.getByRole('alert')).toHaveFocus();
  });

  it('a server failure is a summary too, with the reason and no field link', async () => {
    const onStart = vi.fn().mockResolvedValueOnce('Game 1 could not be started. Try again. Reference: ref_0123456789abcdef');
    render(<GameStartForm game={1} mySide="A" label={label} onStart={onStart} />);
    await userEvent.click(screen.getByRole('radio', { name: 'Other side (Carlos and Bo)' }));
    await userEvent.click(screen.getByRole('button', { name: 'Start game 1' }));
    const summary = await screen.findByRole('alert');
    expect(within(summary).getByRole('heading', { name: 'There is a problem' })).toBeVisible();
    expect(summary).toHaveTextContent('Game 1 could not be started. Try again. Reference: ref_0123456789abcdef');
    expect(within(summary).queryByRole('link')).toBeNull();
    expect(summary).toHaveFocus();
  });
});
