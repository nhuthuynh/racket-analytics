// Match setup pages Q-01..Q-07 (ST-016; flows §5; FR-021, FR-005, FR-043; NFR-037).
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MatchSetup } from '@/components/MatchSetup';
import { ApiError } from '@/lib/api/client';
import type { Match } from '@/lib/api/types';
import { FALLBACK_UPLOAD_POLICY } from '@/lib/api/types';
import { takeHandOff } from '@/lib/upload/handoff';

const ID = '0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10';
const TODAY = { year: 2026, month: 10, day: 5 };
const created = { id: ID, title: 'Singles · 5 Oct 2026', format: 'singles', status: 'awaiting_upload', media: null, created_at: 'x', updated_at: 'x' } as Match;

let navigate: ReturnType<typeof vi.fn>;
beforeEach(() => {
  navigate = vi.fn();
});

function renderSetup(createMatch = vi.fn(async () => created)) {
  render(<MatchSetup api={{ createMatch }} today={TODAY} policy={FALLBACK_UPLOAD_POLICY} navigate={navigate} />);
  return createMatch;
}

const cont = () => userEvent.click(screen.getByRole('button', { name: 'Continue' }));

async function answerSingles(file = new File(['x'.repeat(10)], 'Sat doubles.mp4', { type: 'video/mp4' })) {
  await userEvent.click(screen.getByRole('radio', { name: 'Singles' }));
  await cont();
  await userEvent.click(screen.getByRole('radio', { name: 'Side-out scoring (traditional)' }));
  await cont();
  await userEvent.type(screen.getByLabelText('Side A player'), 'Ivy');
  await userEvent.type(screen.getByLabelText('Side B player'), 'Carlos');
  await cont();
  await userEvent.click(screen.getByRole('radio', { name: 'Ivy (Side A)' }));
  await cont();
  await cont();
  await userEvent.upload(screen.getByLabelText('Choose video'), file);
  await cont();
  return file;
}

describe('MatchSetup', () => {
  it('Q-01: Continue without an answer shows the error summary that links to the first radio', async () => {
    renderSetup();
    expect(screen.getByRole('heading', { level: 1, name: 'Is this a doubles or singles match?' })).toBeVisible();
    await cont();
    const summary = screen.getByRole('alert');
    expect(summary).toHaveTextContent('There is a problem');
    await userEvent.click(within(summary).getByRole('link', { name: 'Select doubles or singles' }));
    expect(screen.getByRole('radio', { name: 'Doubles' })).toHaveFocus();
    expect(document.title).toMatch(/^Error: /);
  });

  it('PD-R3-01: Continue again without an answer moves focus back to the summary', async () => {
    renderSetup();
    await cont();
    const summary = screen.getByRole('alert');
    expect(summary).toHaveFocus();
    await userEvent.click(within(summary).getByRole('link', { name: 'Select doubles or singles' }));
    expect(screen.getByRole('radio', { name: 'Doubles' })).toHaveFocus();
    await cont();
    expect(screen.getByRole('alert')).toHaveFocus();
  });

  it('Q-02: rally scoring is shown, provisional, and cannot be chosen', async () => {
    renderSetup();
    await userEvent.click(screen.getByRole('radio', { name: 'Doubles' }));
    await cont();
    const rally = screen.getByRole('radio', { name: /Rally scoring \(provisional\)/ });
    expect(rally).toHaveAttribute('aria-disabled', 'true');
    await userEvent.click(rally);
    expect(rally).not.toBeChecked();
    expect(screen.getByText('It becomes available once the rules are verified.')).toBeVisible();
  });

  it('Q-03: doubles asks for two players per side and warns about contact details', async () => {
    renderSetup();
    await userEvent.click(screen.getByRole('radio', { name: 'Doubles' }));
    await cont();
    await userEvent.click(screen.getByRole('radio', { name: 'Side-out scoring (traditional)' }));
    await cont();
    const boxes = screen.getAllByRole('textbox');
    expect(boxes).toHaveLength(4);
    expect(within(screen.getByRole('group', { name: 'Side A' })).getAllByRole('textbox')).toHaveLength(2);
    await userEvent.type(boxes[2]!, 'carlos@example.com');
    await userEvent.tab();
    expect(screen.getByText('This looks like contact details. Use a nickname instead.')).toBeVisible();
    await userEvent.type(boxes[0]!, 'Ivy');
    await userEvent.type(boxes[1]!, 'Dana');
    await cont();
    expect(screen.getByRole('link', { name: 'Each side needs two players' })).toBeVisible();
  });

  it('Q-04 lists the nicknames with their side', async () => {
    renderSetup();
    await userEvent.click(screen.getByRole('radio', { name: 'Singles' }));
    await cont();
    await userEvent.click(screen.getByRole('radio', { name: 'Side-out scoring (traditional)' }));
    await cont();
    await userEvent.type(screen.getByLabelText('Side A player'), 'Ivy');
    await userEvent.type(screen.getByLabelText('Side B player'), 'Carlos');
    await cont();
    expect(screen.getByRole('radio', { name: 'Ivy (Side A)' })).toBeVisible();
    expect(screen.getByRole('radio', { name: 'Carlos (Side B)' })).toBeVisible();
  });

  it('Q-07 lists every answer with a "Change" link, and Change returns to the check page', async () => {
    renderSetup();
    await answerSingles();
    expect(screen.getByRole('heading', { level: 1, name: 'Check your answers' })).toBeVisible();
    for (const row of ['Format', 'Scoring system', 'Players', 'You', 'Date', 'Video']) {
      expect(screen.getByText(row, { exact: true })).toBeVisible();
    }
    expect(screen.getAllByRole('link', { name: /^Change/ })).toHaveLength(6);
    expect(screen.getByText('Ivy (Side A)')).toBeVisible();
    await userEvent.click(screen.getByRole('link', { name: 'Change date' }));
    expect(screen.getByRole('heading', { level: 1, name: 'When was the match played?' })).toBeVisible();
    await cont();
    expect(screen.getByRole('heading', { level: 1, name: 'Check your answers' })).toBeVisible();
  });

  it('creates the match with the answers, hands the file to the match page and opens it', async () => {
    const createMatch = renderSetup();
    const file = await answerSingles();
    await userEvent.click(screen.getByRole('button', { name: 'Create match and upload' }));
    await waitFor(() => expect(navigate).toHaveBeenCalledWith(`/matches/${ID}`));
    expect(createMatch).toHaveBeenCalledWith({
      format: 'singles',
      scoring_system: 'side_out',
      played_on: '2026-10-05',
      participants: [
        { slot: 'A1', nickname: 'Ivy', is_me: true },
        { slot: 'B1', nickname: 'Carlos', is_me: false },
      ],
    });
    expect(takeHandOff(ID)).toBe(file);
  });

  it('keeps the answers and shows the reference when the server fails', async () => {
    renderSetup(vi.fn(async () => {
      throw new ApiError(500, 'internal_error', 'ref_5c1e0f3a9b7d4e21');
    }));
    await answerSingles();
    await userEvent.click(screen.getByRole('button', { name: 'Create match and upload' }));
    expect(
      await screen.findByText('Sorry, we could not create your match. Your answers are kept. Try again. Reference: ref_5c1e0f3a9b7d4e21'),
    ).toBeVisible();
    expect(screen.getByText('Ivy (Side A)')).toBeVisible();
    expect(navigate).not.toHaveBeenCalled();
  });

  it('shows the server\'s field errors with the flows copy', async () => {
    renderSetup(vi.fn(async () => {
      throw new ApiError(422, 'validation_failed', null, {
        fields: [{ field: 'participants.me', code: 'choose_one_me' }],
      });
    }));
    await answerSingles();
    await userEvent.click(screen.getByRole('button', { name: 'Create match and upload' }));
    expect(await screen.findByRole('link', { name: 'Choose one player as "me"' })).toBeVisible();
  });
});
