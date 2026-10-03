// "New match" (title and format only), ST-010. Error summary per component checklist §5
// [DPA/DESIGN-13]; busy state per §1.
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '@/lib/api/client';
import type { Match } from '@/lib/api/types';
import { NewMatchForm } from '@/components/NewMatchForm';

const push = vi.fn();
vi.mock('next/navigation', () => ({ useRouter: () => ({ push, refresh: vi.fn() }) }));

const created: Match = {
  id: '0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10',
  title: 'Skeleton test',
  format: 'doubles',
  status: 'awaiting_upload',
  media: null,
  created_at: '2026-10-05T09:12:44.123Z',
  updated_at: '2026-10-05T09:12:44.123Z',
};

beforeEach(() => {
  push.mockReset();
  document.title = 'New match – Racket Analytics';
});

describe('NewMatchForm', () => {
  it('shows an error summary, focuses it and does not call the API when empty', async () => {
    const api = { createMatch: vi.fn() };
    render(<NewMatchForm api={api} />);
    await userEvent.click(screen.getByRole('button', { name: /create match/i }));

    const summary = screen.getByRole('heading', { name: 'There is a problem' }).closest('div');
    expect(summary).toHaveFocus();
    expect(screen.getByRole('link', { name: 'Enter a title for the match' })).toHaveAttribute(
      'href',
      '#title',
    );
    expect(screen.getByRole('link', { name: 'Select the match format' })).toHaveAttribute(
      'href',
      '#format',
    );
    expect(screen.getByLabelText(/title/i)).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByLabelText(/format/i)).toHaveAttribute('aria-invalid', 'true');
    expect(document.title).toBe('Error: New match – Racket Analytics');
    expect(api.createMatch).not.toHaveBeenCalled();
  });

  it('rejects a title that is only spaces', async () => {
    const api = { createMatch: vi.fn() };
    render(<NewMatchForm api={api} />);
    await userEvent.type(screen.getByLabelText(/title/i), '   ');
    await userEvent.selectOptions(screen.getByLabelText(/format/i), 'Doubles');
    await userEvent.click(screen.getByRole('button', { name: /create match/i }));
    expect(screen.getByRole('link', { name: 'Enter a title for the match' })).toBeVisible();
    expect(api.createMatch).not.toHaveBeenCalled();
  });

  it('rejects a title longer than 120 characters', async () => {
    const api = { createMatch: vi.fn() };
    render(<NewMatchForm api={api} />);
    await userEvent.type(screen.getByLabelText(/title/i), 'x'.repeat(121));
    await userEvent.selectOptions(screen.getByLabelText(/format/i), 'Singles');
    await userEvent.click(screen.getByRole('button', { name: /create match/i }));
    expect(
      screen.getByRole('link', { name: 'Title must be 120 characters or fewer' }),
    ).toBeVisible();
    expect(api.createMatch).not.toHaveBeenCalled();
  });

  it('shows a generic problem when the API refuses, without echoing input', async () => {
    const api = { createMatch: vi.fn().mockRejectedValue(new ApiError(422, 'validation_failed')) };
    render(<NewMatchForm api={api} />);
    await userEvent.type(screen.getByLabelText(/title/i), '<b>x</b>');
    await userEvent.selectOptions(screen.getByLabelText(/format/i), 'Doubles');
    await userEvent.click(screen.getByRole('button', { name: /create match/i }));
    expect(
      await screen.findByText('We could not create the match. Check the details and try again.'),
    ).toBeVisible();
    expect(push).not.toHaveBeenCalled();
  });

  it('sends the user to sign in when the session has ended', async () => {
    const api = { createMatch: vi.fn().mockRejectedValue(new ApiError(401, 'unauthenticated')) };
    render(<NewMatchForm api={api} />);
    await userEvent.type(screen.getByLabelText(/title/i), 'Skeleton test');
    await userEvent.selectOptions(screen.getByLabelText(/format/i), 'Doubles');
    await userEvent.click(screen.getByRole('button', { name: /create match/i }));
    await waitFor(() => expect(push).toHaveBeenCalledWith('/'));
  });

  it('creates the match with a trimmed title and opens it', async () => {
    let resolve: (m: Match) => void = () => {};
    const api = {
      createMatch: vi.fn(() => new Promise<Match>((r) => (resolve = r))),
    };
    render(<NewMatchForm api={api} />);
    await userEvent.type(screen.getByLabelText(/title/i), '  Skeleton test  ');
    await userEvent.selectOptions(screen.getByLabelText(/format/i), 'Doubles');
    const button = screen.getByRole('button', { name: /create match/i });
    await userEvent.click(button);

    expect(button).toHaveAttribute('aria-busy', 'true');
    await userEvent.click(button); // double submit is ignored
    expect(api.createMatch).toHaveBeenCalledTimes(1);
    expect(api.createMatch).toHaveBeenCalledWith({ title: 'Skeleton test', format: 'doubles' });

    resolve(created);
    await waitFor(() => expect(push).toHaveBeenCalledWith(`/matches/${created.id}`));
  });
});
