// "Who serves first in game n?" (ST-027). The choice is required; a failed start says so.
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { GameStartForm } from '@/components/tagging/GameStartForm';

const label = (s: 'A' | 'B') => (s === 'A' ? 'Your side (Ivy and Dana)' : 'Other side (Carlos and Bo)');

describe('GameStartForm', () => {
  it('needs a choice before it starts anything', async () => {
    const onStart = vi.fn();
    render(<GameStartForm game={2} mySide="A" label={label} onStart={onStart} />);
    await userEvent.click(screen.getByRole('button', { name: 'Start game 2' }));
    expect(onStart).not.toHaveBeenCalled();
    expect(screen.getByRole('alert')).toHaveTextContent('Choose who serves first in game 2.');
  });

  it('shows the reason when the start fails, and starts with the chosen side', async () => {
    const onStart = vi.fn().mockResolvedValueOnce('Game 1 could not be started. Try again.').mockResolvedValueOnce(null);
    render(<GameStartForm game={1} mySide="B" label={label} intro="Game 0 won." onStart={onStart} />);
    expect(screen.getByText('Game 0 won.')).toBeVisible();
    const radios = screen.getAllByRole('radio');
    expect(radios[0]).toHaveAccessibleName('Other side (Carlos and Bo)');
    await userEvent.click(screen.getByRole('radio', { name: 'Your side (Ivy and Dana)' }));
    await userEvent.click(screen.getByRole('button', { name: 'Start game 1' }));
    expect(onStart).toHaveBeenCalledWith('A');
    expect(await screen.findByRole('alert')).toHaveTextContent('could not be started');
    await userEvent.click(screen.getByRole('button', { name: 'Start game 1' }));
    expect(screen.queryByRole('alert')).toBeNull();
  });
});
