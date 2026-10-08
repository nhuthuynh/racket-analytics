// ST-050 UI, X-01 "Delete this match?" (FR-006, NFR-066; DES FR-UX-90; flows-sprint-03 §4; ADR 0043).
// Negative cases first: Cancel and Esc delete nothing and give focus back; a failure keeps the
// dialog open with the reason and the reference; a second press while deleting sends nothing more;
// a match already deleted elsewhere and a signed-out session go where the design says.
import { act, fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { DeleteMatch } from '@/components/DeleteMatch';
import { ApiError } from '@/lib/api/client';
import type { Match } from '@/lib/api/types';

const ID = '0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10';
const REF = 'ref_0123456789abcdef';
const match: Match = {
  id: ID, title: 'Saturday doubles', format: 'doubles', status: 'video_received', media: null,
  created_at: '2026-10-03T09:00:00Z', updated_at: 'x', played_on: '2026-10-03', upload: null, rejection: null, participants: [],
};

function setup(deleteMatch = vi.fn(async () => {}), m: Match = match) {
  const navigate = vi.fn();
  render(<DeleteMatch match={m} api={{ deleteMatch }} navigate={navigate} />);
  return { deleteMatch, navigate, opener: screen.getByRole('button', { name: 'Delete match' }) };
}

describe('X-01 delete a match (ST-050)', () => {
  it('M-02 says what deleting does before anything is pressed', () => {
    setup();
    expect(screen.getByRole('heading', { level: 2, name: 'Delete this match' })).toBeVisible();
    expect(screen.getByText('Deleting removes the video and everything made from it.')).toBeVisible();
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('Cancel deletes nothing, closes the dialog and gives focus back to "Delete match"', async () => {
    const { deleteMatch, opener } = setup();
    await userEvent.click(opener);
    const dialog = screen.getByRole('dialog', { name: 'Delete this match?' });
    expect(within(dialog).getByRole('button', { name: 'Cancel' })).toHaveFocus();
    await userEvent.click(within(dialog).getByRole('button', { name: 'Cancel' }));
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(opener).toHaveFocus();
    expect(deleteMatch).not.toHaveBeenCalled();
  });

  it('Esc closes it the same way', async () => {
    const { deleteMatch, opener } = setup();
    await userEvent.click(opener);
    act(() => {
      fireEvent(screen.getByRole('dialog'), new Event('cancel', { cancelable: true }));
    });
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(opener).toHaveFocus();
    expect(deleteMatch).not.toHaveBeenCalled();
  });

  it('states the consequences: what goes, that it cannot be undone, the 7 days; no typed word', async () => {
    const { opener } = setup();
    await userEvent.click(opener);
    const dialog = screen.getByRole('dialog', { name: 'Delete this match?' });
    expect(dialog).toHaveTextContent('Saturday doubles · 3 Oct 2026');
    expect(dialog).toHaveTextContent('This deletes the video, tags, score sheet and stats of this match.');
    expect(dialog).toHaveTextContent('It cannot be undone.');
    expect(dialog).toHaveTextContent('The match leaves your account at once. Its stored files are removed within 7 days.');
    expect(dialog).not.toHaveTextContent(/clips|plans/i);
    expect(within(dialog).queryByRole('textbox')).toBeNull();
    expect(dialog).not.toHaveTextContent('The upload in progress stops.');
  });

  it('says the upload stops when one is in progress', async () => {
    const { opener } = setup(undefined, { ...match, status: 'uploading' });
    await userEvent.click(opener);
    expect(screen.getByRole('dialog')).toHaveTextContent('The upload in progress stops.');
  });

  it('a failure keeps the dialog open with the reason and the reference, focus on "Delete match"', async () => {
    const { navigate } = setup(vi.fn().mockRejectedValue(new ApiError(500, 'internal_error', REF)));
    await userEvent.click(screen.getByRole('button', { name: 'Delete match' }));
    const dialog = screen.getByRole('dialog');
    const confirm = within(dialog).getByRole('button', { name: 'Delete match' });
    await userEvent.click(confirm);
    expect(await within(dialog).findByRole('alert')).toHaveTextContent(`The match was not deleted. Try again. Reference: ${REF}`);
    expect(within(dialog).getByRole('button', { name: 'Delete match' })).toHaveFocus();
    expect(navigate).not.toHaveBeenCalled();
  });

  it('offline: says the connection dropped', async () => {
    setup(vi.fn().mockRejectedValue(new ApiError(0, 'network_error')));
    await userEvent.click(screen.getByRole('button', { name: 'Delete match' }));
    await userEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Delete match' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('The match was not deleted because the connection dropped. Try again.');
  });

  it('while deleting: "Deleting…", busy, and a second press sends nothing more', async () => {
    let done: () => void = () => {};
    const deleteMatch = vi.fn(() => new Promise<void>((r) => { done = r; }));
    const { navigate } = setup(deleteMatch);
    await userEvent.click(screen.getByRole('button', { name: 'Delete match' }));
    const dialog = screen.getByRole('dialog');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Delete match' }));
    const busy = within(dialog).getByRole('button', { name: 'Deleting…' });
    expect(busy).toHaveAttribute('aria-busy', 'true');
    await userEvent.click(busy);
    expect(deleteMatch).toHaveBeenCalledTimes(1);
    expect(deleteMatch).toHaveBeenCalledWith(ID);
    await act(async () => done());
    expect(navigate).toHaveBeenCalledWith('/matches?deleted=1');
  });

  it('already deleted on another device (404): goes to the list with that notice', async () => {
    const { navigate } = setup(vi.fn().mockRejectedValue(new ApiError(404, 'not_found')));
    await userEvent.click(screen.getByRole('button', { name: 'Delete match' }));
    await userEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Delete match' }));
    await vi.waitFor(() => expect(navigate).toHaveBeenCalledWith('/matches?deleted=already'));
  });

  it('signed out meanwhile (401): the signed-out path to sign in, nothing deleted', async () => {
    const { navigate } = setup(vi.fn().mockRejectedValue(new ApiError(401, 'unauthenticated')));
    await userEvent.click(screen.getByRole('button', { name: 'Delete match' }));
    await userEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Delete match' }));
    await vi.waitFor(() => expect(navigate).toHaveBeenCalledWith('/'));
  });
});

describe('M-01 after a deletion (flows-sprint-03 §4 "After 202")', () => {
  it('a polite notice without the title, and focus on "Your matches"', async () => {
    const { DeletedNotice } = await import('@/components/DeletedNotice');
    render(
      <>
        <h1 id="page-title" tabIndex={-1}>Your matches</h1>
        <DeletedNotice which="1" />
      </>,
    );
    expect(screen.getByRole('status')).toHaveTextContent('The match was deleted. Its stored files are removed within 7 days.');
    expect(screen.getByRole('heading', { level: 1 })).toHaveFocus();
  });

  it('already deleted: says so; an unknown value shows nothing', async () => {
    const { DeletedNotice } = await import('@/components/DeletedNotice');
    const { unmount } = render(<DeletedNotice which="already" />);
    expect(screen.getByRole('status')).toHaveTextContent('This match was already deleted.');
    unmount();
    render(<DeletedNotice which="<script>" />);
    expect(screen.queryByRole('status')).toBeNull();
  });
});

describe('X-01 entry on M-02', () => {
  it('M-02 ends with "Delete this match", whatever the match status', async () => {
    const { MatchDetail } = await import('@/components/MatchDetail');
    for (const status of ['awaiting_upload', 'video_received', 'probe_failed'] as const) {
      const { unmount } = render(<MatchDetail initialMatch={{ ...match, status }} api={{ getMatch: vi.fn() }} initialFile={null} />);
      const sections = document.querySelectorAll('section');
      expect(sections[sections.length - 1]).toHaveAccessibleName('Delete this match');
      unmount();
    }
  });
});
